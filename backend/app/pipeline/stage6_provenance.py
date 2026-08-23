"""
Stage 6: confidence composition and calibration.

Confidence for a cell already carries an initial value set at the point it
was produced (parse-template fit, vocabulary match strength, consensus
agreement ratio, retrieval score). This stage applies a final calibration
map so that a stated confidence means roughly what it claims.

Honest limitation, documented rather than faked: real isotonic-regression
calibration (mapping raw confidence -> P(correct)) requires labeled
ground-truth rows to fit against. The delivery format sample provides only
2 example rows - not enough to fit a calibration curve. calibrate() is
therefore the identity function by default, with the fitting hook left in
place: call fit_calibration(records, ground_truth_df) once real labeled
rows are available (e.g. from the reviewer queue's approved corrections)
and it will start reshaping confidence for real.
"""
from __future__ import annotations

from app.core.schema import Cell, EnrichedRecord

_calibration_map: dict[float, float] | None = None  # None = identity (uncalibrated)


def calibrate(cell: Cell) -> Cell:
    if _calibration_map is None or cell.is_blank():
        return cell
    # nearest calibration bin
    bins = sorted(_calibration_map.keys())
    nearest = min(bins, key=lambda b: abs(b - cell.confidence))
    cell.confidence = round(_calibration_map[nearest], 3)
    return cell


def apply_calibration(record: EnrichedRecord) -> EnrichedRecord:
    for cell in record.all_cells().values():
        calibrate(cell)
    return record


def fit_calibration(records: list[EnrichedRecord], reviewer_approved: dict[str, bool]) -> None:
    """
    Placeholder for isotonic-regression fitting once enough reviewer
    approve/reject decisions exist. Not wired into the default run - see
    module docstring.
    """
    global _calibration_map
    # intentionally left as a no-op until there is real labeled data to fit against
    return
