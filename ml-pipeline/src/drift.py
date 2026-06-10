"""Stage 4 — data-drift check with Evidently.

Compares the training distribution against 'current' traffic (the test
split here; in production, a window of recent inference inputs). Writes
an HTML report for humans and drift.json for machines/CI gates.
"""

import json

import pandas as pd

from common import DATA_DIR, FEATURES, REPORTS_DIR, load_params


def run_evidently(reference: pd.DataFrame, current: pd.DataFrame):
    """Evidently moved its public API in 0.7 — support both layouts."""
    try:  # evidently >= 0.7
        from evidently import Report
        from evidently.presets import DataDriftPreset

        report = Report([DataDriftPreset()])
        result = report.run(reference_data=reference, current_data=current)
        return result.dict(), lambda path: result.save_html(str(path))
    except ImportError:  # evidently < 0.7
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=reference, current_data=current)
        return report.as_dict(), lambda path: report.save_html(str(path))


def summarize(result: dict, alert_share: float) -> dict:
    """Pull per-column drift flags out of either result schema."""
    drifted, total = 0, 0
    for metric in result.get("metrics", []):
        name = str(metric.get("metric_name", metric.get("metric", "")))
        value = metric.get("value", metric.get("result", {}))
        if name.startswith("DriftedColumnsCount") and isinstance(value, dict):
            # evidently >= 0.7 preset: authoritative count over all columns
            drifted = int(value.get("count", 0))
            total = max(total, len(FEATURES))
            break
        if name.startswith("ValueDrift") and isinstance(value, (int, float)):
            total += 1
            if value < 0.05:  # p-value: small means drifted
                drifted += 1
    share = drifted / total if total else 0.0
    return {
        "columns_checked": total,
        "columns_drifted": drifted,
        "drift_share": round(share, 3),
        "alert": share >= alert_share,
    }


def main():
    alert_share = load_params()["drift"]["alert_share"]
    reference = pd.read_csv(DATA_DIR / "train.csv")[FEATURES]
    current = pd.read_csv(DATA_DIR / "test.csv")[FEATURES]

    REPORTS_DIR.mkdir(exist_ok=True)
    result, save_html = run_evidently(reference, current)
    save_html(REPORTS_DIR / "drift.html")

    summary = summarize(result, alert_share)
    with open(REPORTS_DIR / "drift.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"drift: {summary}")
    if summary["alert"]:
        raise SystemExit("drift: ALERT — distribution shift exceeds threshold")


if __name__ == "__main__":
    main()
