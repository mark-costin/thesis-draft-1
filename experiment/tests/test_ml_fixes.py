"""
Tests to write BEFORE the code changes in the action plan (TDD: red first).

Place at: experiment/tests/test_ml_fixes.py
Run:      uv run pytest experiment/tests -W error::RuntimeWarning -q

Order:
  1. Run the add_derived snapshot step (bottom of file) on the CURRENT, unfixed code.
  2. Run pytest -> threshold_metrics tests must FAIL (function doesn't exist yet).
  3. Implement threshold_metrics -> tests go green.
  4. Apply the add_derived fix -> snapshot + no-warning tests must stay/go green.
"""
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiment.src.ml import data as D
from experiment.src.ml import evaluate as E


# ---------------------------------------------------------------------------
# threshold_metrics  (Phase C, Step 4)
# ---------------------------------------------------------------------------

def test_all_negative_predictor_shows_accuracy_paradox():
    """10% prevalence, predict 'no disease' for everyone: 90% accuracy, useless model."""
    y = np.array([1] * 10 + [0] * 90)
    p = np.zeros(100)
    m = E.threshold_metrics(y, p, threshold=0.5)
    assert m["accuracy"] == pytest.approx(0.90)
    assert m["balanced_accuracy"] == pytest.approx(0.50)
    assert m["sensitivity"] == 0.0
    assert m["specificity"] == 1.0
    assert math.isnan(m["PPV"])  # no predicted positives -> undefined, not 0
    assert m["TP"] + m["FN"] == 10


def test_matches_hand_computed_confusion_matrix():
    y = [1, 1, 1, 0, 0, 0, 0, 0]
    p = [0.9, 0.6, 0.1, 0.7, 0.2, 0.1, 0.3, 0.05]
    m = E.threshold_metrics(y, p, threshold=0.5)
    assert (m["TP"], m["FN"], m["FP"], m["TN"]) == (2, 1, 1, 4)
    assert m["sensitivity"] == pytest.approx(2 / 3)
    assert m["specificity"] == pytest.approx(4 / 5)
    assert m["PPV"] == pytest.approx(2 / 3)
    assert m["NPV"] == pytest.approx(4 / 5)
    assert m["accuracy"] == pytest.approx(6 / 8)
    assert m["F1"] == pytest.approx(2 / 3)


def test_probability_equal_to_threshold_counts_as_positive():
    m = E.threshold_metrics([1, 0], [0.5, 0.49], threshold=0.5)
    assert (m["TP"], m["FP"], m["TN"], m["FN"]) == (1, 0, 1, 0)


def test_threshold_is_respected():
    y = [1, 0]
    p = [0.3, 0.1]
    assert E.threshold_metrics(y, p, threshold=0.5)["TP"] == 0
    assert E.threshold_metrics(y, p, threshold=0.2)["TP"] == 1


def test_single_class_subgroup_does_not_crash():
    """Rare subgroups / bootstrap resamples can contain no positives."""
    m = E.threshold_metrics([0, 0, 0], [0.1, 0.9, 0.2], threshold=0.5)
    assert math.isnan(m["sensitivity"])
    assert m["specificity"] == pytest.approx(2 / 3)


def test_mismatched_lengths_raise():
    """Guards the notebook bug where DEV[d]['p'] and ev['y'] come from different rows."""
    with pytest.raises(ValueError):
        E.threshold_metrics([0, 1, 0], [0.2, 0.8], threshold=0.5)


# ---------------------------------------------------------------------------
# add_derived zero-division fix  (Phase B, Step 3a)
# Characterization test: the fix must not change any derived value.
# ---------------------------------------------------------------------------

SNAPSHOT = Path("experiment/tests/snapshots/derived_before_fix.parquet")


def load_inputs():
    """FILL IN: return (df, vel) exactly as data.py builds them before calling add_derived."""
    raise NotImplementedError("wire this to your data.py loader")


def make_snapshot():
    """Run ONCE on the unfixed code:
    uv run python -c "from experiment.tests.test_ml_fixes import make_snapshot; make_snapshot()"
    """
    df, vel = load_inputs()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    D.add_derived(df.copy(), vel).to_parquet(SNAPSHOT)


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="take the snapshot on unfixed code first")
def test_add_derived_output_unchanged_by_fix():
    df, vel = load_inputs()
    out = D.add_derived(df.copy(), vel)
    pd.testing.assert_frame_equal(out, pd.read_parquet(SNAPSHOT))


def test_add_derived_emits_no_runtime_warning():
    df, vel = load_inputs()
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        D.add_derived(df.copy(), vel)


def test_first_visit_velocity_is_nan_not_inf():
    df, vel = load_inputs()
    out = D.add_derived(df.copy(), vel)
    v_cols = [c for c in out.columns if c.startswith("v_")]
    assert not np.isinf(out[v_cols].to_numpy(dtype=float)).any()