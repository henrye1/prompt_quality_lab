"""Streamlit UI for Prompt Quality Lab. Composes the optimiser modules."""
from __future__ import annotations

import html as html_lib
import os
from datetime import datetime

import streamlit as st
from anthropic import Anthropic

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import docx
except ImportError:
    docx = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from credit_datasets import dataset_root, load_records
from credit_datasets.schema import QualityGrade
from prompt_quality_lab.anthropic_client import call_claude, evaluate_against_expected
from prompt_quality_lab.config import AVAILABLE_MODELS
from prompt_quality_lab.dataset_bridge import records_to_prompts
from prompt_quality_lab.loaders import load_prompts
from prompt_quality_lab.optimisers import langchain_template as lct
from prompt_quality_lab.optimisers.dspy_bootstrap import dspy_style_bootstrap
from prompt_quality_lab.optimisers.prompt_improver import anthropic_prompt_improver
from prompt_quality_lab.optimisers.variants import generate_variants


def _sidebar() -> tuple[str, str, list, list, list, list, list[dict]]:
    """Render the sidebar.

    Returns (api_key, model, uploaded_files, input_docs, target_docs,
    few_shot_files, dataset_prompts). The dataset_prompts are already-resolved
    dicts in the optimiser's expected shape — they bypass load_prompts().
    """
    with st.sidebar:
        st.header("⚙️ Setup")
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key:
            st.success("✓ Anthropic API key loaded from `.env`")
            api_key = env_key
        else:
            api_key = st.text_input(
                "Anthropic API key",
                type="password",
                help="Get one at https://console.anthropic.com/ — or save it to `.env`",
            )
        model = st.selectbox("Model", AVAILABLE_MODELS, index=0)
        st.divider()
        st.subheader("📂 Upload prompts")
        uploaded = st.file_uploader(
            "CSV / JSON / .txt / .xlsx / .xlsm / .docx / .pdf — multiple OK",
            type=["csv", "json", "txt", "md", "xlsx", "xls", "xlsm", "docx", "pdf"],
            accept_multiple_files=True,
        )
        st.divider()
        st.subheader("� Upload credit paper input documents")
        input_docs = st.file_uploader(
            "Upload financials, reports, and other input documents for credit paper generation",
            type=["csv", "json", "txt", "md", "xlsx", "xls", "xlsm", "docx", "pdf"],
            accept_multiple_files=True,
            help="These files are treated as the input source for the credit paper prompt.",
        )
        st.divider()
        st.subheader("📥 Upload target style example documents")
        target_docs = st.file_uploader(
            "Upload example credit reports or target output documents to replicate",
            type=["txt", "md", "docx", "pdf"],
            accept_multiple_files=True,
            help="These files are used to capture the desired reporting style and output format.",
        )
        st.divider()
        st.subheader("�📁 Upload few-shot example files (optional)")
        few_shot = st.file_uploader(
            "Upload files containing few-shot examples (these should include expected outputs)",
            type=["csv", "json", "txt", "md", "xlsx", "xls", "xlsm", "docx", "pdf"],
            accept_multiple_files=True,
            help="These files will be used as labelled few-shot examples for the DSPy tab.",
        )
        if pd is None or docx is None or PyPDF2 is None:
            st.warning(
                "PDF/Word/Excel uploads require extra libraries. Install:\n"
                "`pip install pandas openpyxl python-docx PyPDF2` "
                "or run `uv sync` to install all requirements."
            )
        st.divider()
        dataset_prompts = _dataset_picker()
        st.divider()
        with st.expander("Input format hints"):
            st.markdown(
                """
**CSV** — columns: `id, prompt, expected_output` *(expected_output optional)*

**JSON** — list of objects:
```json
[
  {"id": "p1", "prompt": "...", "expected_output": "..."}
]
```

**.txt** — one prompt per file; filename becomes the ID.

**Excel (.xls/.xlsx/.xlsm)** — sheets/tables with columns `id, prompt, expected_output` (or `prompt_text`).

**Word (.docx)** / **PDF (.pdf)** — text is split by blank lines. To load multiple prompts in one file, use sections like:

```
ID: example-1
Prompt: Translate the following text to French.
Expected: Traduire le texte suivant en français.

ID: example-2
Prompt: Summarise the article in two sentences.
Expected: Résumer l'article en deux phrases.
```

If the file contains a single block, it will be loaded as a single prompt.
"""
            )
    return api_key, model, uploaded, input_docs, target_docs, few_shot, dataset_prompts


def _dataset_picker() -> list[dict]:
    """Render the 'Load from Dataset Manager' picker. Returns selected records
    already resolved to the optimiser's prompt-dict shape.

    Records without input files are dropped (handled in records_to_prompts).
    Records without a gold file pass through with empty expected_output, which
    just means the optimisers run them unscored — same behavior as for uploaded
    files that lack expected outputs.
    """
    st.subheader("📚 Load from Dataset Manager")
    try:
        records = load_records()
    except (OSError, ValueError) as e:
        st.caption(f"Could not read dataset: {e}")
        return []

    if not records:
        st.caption("No records yet — add some via the Dataset Manager page.")
        return []

    gold_only = st.checkbox(
        "Gold-graded only",
        value=True,
        key="dataset_gold_only",
        help="Filter to records marked gold. Uncheck to also see silver/bronze.",
    )
    visible = [r for r in records if not gold_only or r.quality_grade == QualityGrade.GOLD]
    if not visible:
        st.caption("No gold-graded records. Uncheck the filter to see all.")
        return []

    options = {f"{r.id} — {r.company_name} ({r.quality_grade.value})": r for r in visible}
    chosen_labels = st.multiselect(
        "Pick records to feed into the optimisers",
        options=list(options.keys()),
        key="dataset_chosen",
    )
    if not chosen_labels:
        return []

    chosen_records = [options[label] for label in chosen_labels]
    return records_to_prompts(chosen_records, dataset_root())


def _load_target_style_examples(target_docs: list[dict]) -> list[dict]:
    """Convert raw target documents into labelled style examples."""
    examples = []
    for d in target_docs:
        text = d["prompt"].strip()
        if not text:
            continue
        examples.append(
            {
                "id": d["id"],
                "prompt": (
                    "Generate a credit paper in the same style and structure as the example output below."
                ),
                "expected_output": text,
                "source": d.get("source", "target-doc"),
            }
        )
    return examples


def _combine_input_documents(input_docs: list[dict]) -> str:
    """Combine uploaded input documents into a single credit paper prompt."""
    combined = []
    for doc in input_docs:
        combined.append(f"---\n{doc['id']}\n{doc['prompt'].strip()}")
    return "\n\n".join(combined)


def _tab_prompt_improver(client: Anthropic, prompts: list[dict], model: str) -> None:
    st.subheader("Rewrite each prompt for clarity (meta-prompting)")
    st.caption(
        "Claude rewrites your prompt to be clearer, more specific, and better structured. "
        "If you have expected outputs, both versions are scored."
    )
    also_score = st.checkbox(
        "Score original vs improved (uses extra API calls)",
        value=True,
        key="improver_score",
    )
    if st.button("🚀 Improve all prompts", key="improver_run", type="primary"):
        for p in prompts:
            with st.expander(f"📝 {p['id']}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original**")
                    st.code(p["prompt"], language="markdown")
                with col2:
                    st.markdown("**Improved**")
                    with st.spinner("Improving..."):
                        improved = anthropic_prompt_improver(client, p["prompt"], model)
                    st.code(improved, language="markdown")
                    # Provide brief context for the improved prompt
                    st.markdown(
                        "**Context:** This improved prompt is a rewritten version that aims to clarify intent, remove ambiguity, and better structure the required output while preserving the original meaning."
                    )
                    # Build download content with metadata so the file can be used directly for testing
                    timestamp = datetime.utcnow().isoformat() + "Z"
                    download_text = (
                        f"## Improved Prompt\n\n{improved}\n\n---\nOriginal prompt:\n{p['prompt']}\n\nModel: {model}\nTimestamp: {timestamp}\n"
                    )
                    st.download_button(
                        "📥 Download improved prompt",
                        data=download_text,
                        file_name=f"{p['id']}_improved.txt",
                        mime="text/plain",
                        key=f"download_{p['id']}",
                    )

                    # Add a copy-to-clipboard button using a small HTML component
                    escaped = html_lib.escape(improved)
                    copy_html = f"""
<button onclick="navigator.clipboard.writeText(document.getElementById('impr_{p['id']}').innerText)">Copy improved prompt</button>
<pre id="impr_{p['id']}" style="display:none;">{escaped}</pre>
"""
                    st.components.v1.html(copy_html, height=40)

                if also_score and p["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, orig_score = evaluate_against_expected(
                            client, p["prompt"], p["expected_output"], model
                        )
                        _, new_score = evaluate_against_expected(
                            client, improved, p["expected_output"], model
                        )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Original score", orig_score)
                    c2.metric("Improved score", new_score)
                    if orig_score is not None and new_score is not None:
                        c3.metric("Δ", round(new_score - orig_score, 2))


def _tab_credit_paper(
    client: Anthropic,
    input_docs: list[dict],
    target_style_docs: list[dict],
    model: str,
) -> None:
    st.subheader("Credit Paper Optimiser")
    st.caption(
        "Use your uploaded financial inputs and target report examples to generate a credit paper in the desired style."
    )

    if not input_docs:
        st.warning(
            "Upload credit paper input documents in the sidebar to use this tab."
        )
        return
    if not target_style_docs:
        st.warning(
            "Upload target style example documents in the sidebar to use this tab."
        )
        return

    if st.button("🚀 Generate credit paper", key="credit_run", type="primary"):
        combined_input = _combine_input_documents(input_docs)
        style_examples = _load_target_style_examples(target_style_docs)
        augmented = dspy_style_bootstrap(combined_input, style_examples)
        with st.spinner("Generating credit paper..."):
            output = call_claude(client, augmented, model=model)

        st.markdown("**Generated credit paper**")
        st.code(output, language="markdown")

        with st.expander("Input documents used"):
            for doc in input_docs:
                st.markdown(f"**{doc['id']}**")
                st.code(doc["prompt"], language="markdown")

        with st.expander("Target style examples used"):
            for ex in style_examples:
                st.markdown(f"**{ex['id']}** (source: {ex.get('source', 'target-doc')})")
                st.code(ex["expected_output"], language="markdown")


def _tab_dspy(client: Anthropic, prompts: list[dict], labelled: list[dict], model: str) -> None:
    st.subheader("Bootstrap few-shot examples (DSPy-style)")
    st.caption(
        f"Uses your **{len(labelled)}** labelled prompt(s) as few-shot examples "
        "for the rest, then compares baseline vs few-shot output."
    )
    if not labelled:
        st.warning(
            "Need at least one prompt with `expected_output` filled in "
            "to use as a few-shot example."
        )
        return

    n_shots = st.slider(
        "Few-shot examples per prompt",
        1,
        min(5, len(labelled)),
        min(3, len(labelled)),
    )
    if st.button("🚀 Run DSPy-style optimisation", key="dspy_run", type="primary"):
        for target in prompts:
            fs_pool = [p for p in labelled if p["id"] != target["id"]][:n_shots]
            augmented = dspy_style_bootstrap(target["prompt"], fs_pool)

            with st.expander(f"📝 {target['id']}", expanded=True):
                sources = sorted({e.get("source", "unknown") for e in fs_pool})
                st.markdown(
                    f"**Few-shot examples used:** {[e['id'] for e in fs_pool] or 'none'}"
                )
                st.markdown(f"**Example sources:** {sources}")
                with st.spinner("Running baseline + few-shot..."):
                    baseline = call_claude(client, target["prompt"], model=model)
                    boosted = call_claude(client, augmented, model=model)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Baseline output**")
                    st.write(baseline)
                with col2:
                    st.markdown("**Few-shot output**")
                    st.write(boosted)

                if target["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, b_score = evaluate_against_expected(
                            client, target["prompt"], target["expected_output"], model
                        )
                        _, n_score = evaluate_against_expected(
                            client, augmented, target["expected_output"], model
                        )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Baseline score", b_score)
                    c2.metric("Few-shot score", n_score)
                    if b_score is not None and n_score is not None:
                        c3.metric("Δ", round(n_score - b_score, 2))

                with st.expander("View augmented prompt"):
                    st.code(augmented, language="markdown")


def _tab_variants(client: Anthropic, prompts: list[dict], model: str) -> None:
    st.subheader("Generate N variants and score side-by-side (promptfoo-style)")
    st.caption(
        "Claude generates rewrites of each prompt; all variants run; outputs are "
        "scored against `expected_output` if provided."
    )
    n_variants = st.slider("Number of variants per prompt", 2, 5, 3, key="n_variants")
    if st.button("🚀 Generate & compare variants", key="variants_run", type="primary"):
        for p in prompts:
            with st.expander(f"📝 {p['id']}", expanded=True):
                with st.spinner("Generating variants..."):
                    variants = generate_variants(client, p["prompt"], n_variants, model)

                all_versions = [("Original", p["prompt"])] + [
                    (f"Variant {i+1}", v) for i, v in enumerate(variants)
                ]

                rows = []
                for label, text in all_versions:
                    with st.spinner(f"Running {label}..."):
                        actual, score = evaluate_against_expected(
                            client, text, p["expected_output"], model
                        )
                    rows.append(
                        {"version": label, "score": score, "prompt": text, "output": actual}
                    )

                summary = [{"version": r["version"], "score": r["score"]} for r in rows]
                st.markdown("**Score summary**")
                st.dataframe(summary, use_container_width=True)

                for r in rows:
                    with st.expander(f"{r['version']}  —  score: {r['score']}"):
                        st.markdown("**Prompt**")
                        st.code(r["prompt"], language="markdown")
                        st.markdown("**Output**")
                        st.write(r["output"])


def _tab_langchain(client: Anthropic, prompts: list[dict], api_key: str, model: str) -> None:
    st.subheader("LangChain PromptTemplate + simple evals")
    st.caption(
        "Wraps each prompt as a `PromptTemplate`. If the prompt contains `{variables}`, "
        "you'll be asked to fill them in. Then runs via LangChain's Anthropic wrapper."
    )
    if not lct.AVAILABLE:
        st.warning(
            "LangChain not installed. Run:\n"
            "```\npip install langchain langchain-anthropic langchain-core\n```"
        )
        return

    llm = lct.ChatAnthropic(model=model, anthropic_api_key=api_key)
    for p in prompts:
        with st.expander(f"📝 {p['id']}", expanded=True):
            try:
                tmpl = lct.PromptTemplate.from_template(p["prompt"])
            except Exception as e:
                st.error(f"Couldn't parse as template: {e}")
                continue

            vars_needed = list(tmpl.input_variables)
            st.markdown(f"**Input variables:** `{vars_needed or 'none'}`")

            if vars_needed:
                vals: dict[str, str] = {}
                for v in vars_needed:
                    vals[v] = st.text_input(
                        f"Value for `{v}`", key=f"lc_{p['id']}_{v}"
                    )
                ready = all(v.strip() for v in vals.values())
            else:
                vals = {}
                ready = True

            if ready and st.button(f"Run {p['id']}", key=f"lc_run_{p['id']}"):
                rendered = tmpl.format(**vals) if vals else p["prompt"]
                with st.spinner("Calling Claude via LangChain..."):
                    response = llm.invoke(rendered).content
                st.markdown("**Output**")
                st.write(response)
                if p["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, score = evaluate_against_expected(
                            client, rendered, p["expected_output"], model
                        )
                    st.metric("Score vs expected", score)


def main() -> None:
    st.set_page_config(page_title="Prompt Quality Lab", page_icon="🧪", layout="wide")
    st.title("🧪 Prompt Quality Lab")
    st.caption(
        "Test four prompt-optimisation strategies on your own prompts — powered by Anthropic Claude"
    )

    (
        api_key,
        model,
        uploaded,
        input_uploaded,
        target_uploaded,
        few_uploaded,
        dataset_prompts,
    ) = _sidebar()

    if not api_key:
        st.warning("👈 Add your Anthropic API key in the sidebar to begin.")
        st.stop()
    if not uploaded and not input_uploaded and not dataset_prompts:
        st.info(
            "👈 Upload one or more prompt files, credit paper input documents, "
            "or pick records from the Dataset Manager in the sidebar."
        )
        st.stop()

    client = Anthropic(api_key=api_key)
    prompts, warnings = load_prompts(uploaded)
    # Dataset Manager records are already in the right shape; concatenate.
    prompts = prompts + dataset_prompts
    for w in warnings:
        st.warning(w)

    input_docs: list[dict] = []
    if input_uploaded:
        input_docs, input_warnings = load_prompts(input_uploaded)
        for w in input_warnings:
            st.warning(w)

    target_docs: list[dict] = []
    if target_uploaded:
        target_docs, target_warnings = load_prompts(target_uploaded)
        for w in target_warnings:
            st.warning(w)

    # Load any few-shot example files and merge their labelled prompts into the labelled pool
    few_prompts: list[dict] = []
    if few_uploaded:
        fp, fw = load_prompts(few_uploaded)
        few_prompts = fp
        for w in fw:
            st.warning(w)

    if not prompts and not input_docs:
        st.error("No prompts or input documents could be loaded. Check the file format hints in the sidebar.")
        st.stop()

    labelled = [p for p in prompts if p["expected_output"].strip()]
    # Add few-shot prompts that include expected outputs (these are treated as labelled examples)
    labelled_from_few = [p for p in few_prompts if p["expected_output"].strip()]
    if labelled_from_few:
        sources = sorted({p.get("source", "unknown") for p in labelled_from_few})
        st.info(
            f"Added {len(labelled_from_few)} few-shot example(s) from the separate upload: {sources}"
        )
        labelled.extend(labelled_from_few)
    elif few_uploaded:
        st.warning(
            "No labelled few-shot prompts were loaded from the separate upload. "
            "Check the preview below and make sure each example includes `expected_output`."
        )

    summary_parts = []
    if prompts:
        summary_parts.append(f"**{len(prompts)}** main prompt(s)")
    if input_docs:
        summary_parts.append(f"**{len(input_docs)}** input document(s)")
    summary_parts.append(f"**{len(labelled)}** labelled prompt(s)")
    st.success(
        "Loaded " + " — ".join(summary_parts) + " (usable as eval data where applicable)."
    )

    if prompts:
        with st.expander("👀 Preview loaded prompts"):
            preview = [
                {**p, "source": p.get("source", "uploaded")}
                for p in prompts
            ]
            st.dataframe(preview, use_container_width=True)

    if input_docs:
        with st.expander("👀 Preview credit paper input documents"):
            preview_inputs = [
                {**p, "source": p.get("source", "input-doc")}
                for p in input_docs
            ]
            st.dataframe(preview_inputs, use_container_width=True)

    if target_docs:
        with st.expander("👀 Preview target style documents"):
            preview_targets = [
                {**p, "source": p.get("source", "target-doc")}
                for p in target_docs
            ]
            st.dataframe(preview_targets, use_container_width=True)

    if few_uploaded:
        with st.expander("👀 Preview uploaded few-shot examples"):
            preview_few = [
                {**p, "source": p.get("source", "few-shot upload")}
                for p in few_prompts
            ]
            if preview_few:
                st.dataframe(preview_few, use_container_width=True)
            else:
                st.info(
                    "No prompts were extracted from the few-shot upload. "
                    "See warning messages above for details."
                )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🔧 Prompt Improver",
            "📊 DSPy-style Few-Shot",
            "⚖️ Variant Comparison",
            "🔗 LangChain + Evals",
            "🧾 Credit Paper",
        ]
    )
    with tab1:
        _tab_prompt_improver(client, prompts, model)
    with tab2:
        _tab_dspy(client, prompts, labelled, model)
    with tab3:
        _tab_variants(client, prompts, model)
    with tab4:
        _tab_langchain(client, prompts, api_key, model)
    with tab5:
        _tab_credit_paper(client, input_docs, target_docs, model)


if __name__ == "__main__":
    main()
