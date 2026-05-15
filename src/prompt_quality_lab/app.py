"""Streamlit UI for Prompt Quality Lab. Composes the optimiser modules."""
from __future__ import annotations

import os
from datetime import datetime
import html as html_lib

import streamlit as st
from anthropic import Anthropic

from prompt_quality_lab.anthropic_client import call_claude, evaluate_against_expected
from prompt_quality_lab.config import AVAILABLE_MODELS
from prompt_quality_lab.loaders import load_prompts
from prompt_quality_lab.optimisers import langchain_template as lct
from prompt_quality_lab.optimisers.dspy_bootstrap import dspy_style_bootstrap
from prompt_quality_lab.optimisers.prompt_improver import anthropic_prompt_improver
from prompt_quality_lab.optimisers.variants import generate_variants


def _sidebar() -> tuple[str, str, list, list]:
    """Render the sidebar. Returns (api_key, model, uploaded_files, few_shot_files)."""
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
        st.subheader("📁 Upload few-shot example files (optional)")
        few_shot = st.file_uploader(
            "Upload files containing few-shot examples (these should include expected outputs)",
            type=["csv", "json", "txt", "md", "xlsx", "xls", "xlsm", "docx", "pdf"],
            accept_multiple_files=True,
            help="These files will be used as labelled few-shot examples for the DSPy tab.",
        )
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

**Word (.docx)** — full document text will be treated as a single prompt.

**PDF (.pdf)** — text will be extracted and treated as a single prompt.
"""
            )
    return api_key, model, uploaded, few_shot


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
                st.markdown(
                    f"**Few-shot examples used:** {[e['id'] for e in fs_pool] or 'none'}"
                )
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

    api_key, model, uploaded = _sidebar()

    if not api_key:
        st.warning("👈 Add your Anthropic API key in the sidebar to begin.")
        st.stop()
    if not uploaded:
        st.info("👈 Upload one or more prompt files in the sidebar.")
        st.stop()

    client = Anthropic(api_key=api_key)
    prompts, warnings = load_prompts(uploaded)
    for w in warnings:
        st.warning(w)
    if not prompts:
        st.error("No prompts could be loaded. Check the file format hints in the sidebar.")
        st.stop()

    labelled = [p for p in prompts if p["expected_output"].strip()]
    st.success(
        f"Loaded **{len(prompts)}** prompt(s) — **{len(labelled)}** have expected outputs "
        "(usable as eval data)."
    )
    with st.expander("👀 Preview loaded prompts"):
        st.dataframe(prompts, use_container_width=True)

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🔧 Prompt Improver",
            "📊 DSPy-style Few-Shot",
            "⚖️ Variant Comparison",
            "🔗 LangChain + Evals",
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


if __name__ == "__main__":
    main()
