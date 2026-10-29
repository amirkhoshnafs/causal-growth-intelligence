import numpy as np
import pandas as pd

from app import (
    analyze_campaign,
    build_caveats,
    build_negative_demo_data,
    build_positive_demo_data,
    estimate_confidence,
    run_sensitivity_checks,
    validate_and_clean,
)


def test_positive_case_is_reproducible():
    assert build_positive_demo_data().equals(build_positive_demo_data())
    df, errors = validate_and_clean(build_positive_demo_data())
    assert errors == []
    r = analyze_campaign(df)
    assert r.estimated_uplift > 0
    assert r.confidence == "Medium"
    assert any("Discount" in c for c in r.caveats)
    assert r.campaign_spend > 0


def test_negative_case_is_reproducible_and_not_optimistic():
    df, errors = validate_and_clean(build_negative_demo_data())
    assert not errors
    r = analyze_campaign(df)
    assert r.estimated_uplift < 0
    assert "Pause or revise" in r.next_action


def test_required_column_validation():
    df = pd.DataFrame({"date": ["2026-01-01"]})
    _, errors = validate_and_clean(df)
    assert any("Missing required columns" in e for e in errors)


def test_valid_group_period_cells_required():
    df = build_positive_demo_data()
    df = df[~((df["group"] == "control") & (df["period"] == "pre"))]
    _, errors = validate_and_clean(df)
    assert any("Missing required group-period" in e for e in errors)


def test_bad_group_values_rejected():
    df = build_positive_demo_data()
    df.loc[0,"group"] = "mystery"
    _, errors = validate_and_clean(df)
    assert any("only contain treatment or control" in e for e in errors)


def test_discount_and_stock_caveats():
    df = build_positive_demo_data()
    df.loc[(df["period"]=="post") & (df["group"]=="treatment"),"stock_status"] = "stockout"
    clean, errors = validate_and_clean(df)
    assert not errors
    caveats = build_caveats(clean)
    assert any("Discount" in x for x in caveats)
    assert any("Stock effects" in x for x in caveats)


def test_zero_spend_returns_no_spend_ratio():
    df = build_positive_demo_data()
    df["ad_spend"] = 0
    clean, errors = validate_and_clean(df)
    assert not errors
    r = analyze_campaign(clean)
    assert r.estimated_roi is None
    assert "Sensitivity unavailable" in run_sensitivity_checks(r)


def test_small_sample_heuristic_confidence():
    assert estimate_confidence(pd.DataFrame(index=range(5)),[]) == "Low"


def test_sensitivity_scenarios_use_deterministic_perturbations():
    clean,errors = validate_and_clean(build_positive_demo_data())
    assert not errors
    result=analyze_campaign(clean)
    s=run_sensitivity_checks(result)
    assert len(s)==3
    assert all("x" in item for item in s.values())


def test_pre_post_growth_gap_matches_original_documented_formula():
    clean, errors=validate_and_clean(build_positive_demo_data())
    assert not errors
    r=analyze_campaign(clean)
    assert np.isclose(r.estimated_uplift, r.treatment_growth-r.control_growth)
    # The test confirms the actual implementation, not causal identification.
    expected=r.treatment_post_avg*r.estimated_uplift*r.n_post_days
    assert np.isclose(r.incremental_revenue, expected)
