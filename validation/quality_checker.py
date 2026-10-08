"""Quality checker: thin wrapper turning QualityReport into UI-ready summary."""
from __future__ import annotations

from models.schemas import QualityReport


def quality_summary(report: QualityReport | dict | None) -> dict:
    if report is None:
        return {"overall": 0, "label": "Not evaluated", "rows": []}
    d = report.as_dict() if isinstance(report, QualityReport) else dict(report)
    overall = int(d.get("overall", 0))
    label = (
        "Excellent" if overall >= 90 else
        "Good" if overall >= 75 else
        "Fair" if overall >= 55 else "Needs improvement"
    )
    rows = [
        ("Relevance", d.get("relevance", 0)),
        ("Consistency", d.get("consistency", 0)),
        ("Factuality", d.get("factuality", 0)),
        ("Completeness", d.get("completeness", 0)),
        ("Format", d.get("format_compliance", d.get("format", 0))),
    ]
    return {"overall": overall, "label": label, "rows": rows,
            "notes": d.get("notes", "")}
