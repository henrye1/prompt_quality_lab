"""credit_datasets — shared golden labelled dataset.

Public API:
    Record, AssetClass, QualityGrade, Source, ValidationReport
    load_records, get_record, add_record, update_record, delete_record
    next_id, validate
    dataset_root
"""

from credit_datasets.paths import dataset_root
from credit_datasets.schema import (
    AssetClass,
    QualityGrade,
    Record,
    Source,
    ValidationReport,
)
from credit_datasets.store import (
    add_record,
    delete_record,
    get_record,
    load_records,
    next_id,
    update_record,
    validate,
)

__version__ = "0.1.0"

__all__ = [
    "AssetClass",
    "QualityGrade",
    "Record",
    "Source",
    "ValidationReport",
    "add_record",
    "dataset_root",
    "delete_record",
    "get_record",
    "load_records",
    "next_id",
    "update_record",
    "validate",
    "__version__",
]
