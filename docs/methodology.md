# Methodology — what the app measures and what it does not

## Inputs and quantities

The current source computes average daily `revenue` in the four available group-period cells:

| | Pre | Post |
|---|---:|---:|
| Treatment | `T_pre` | `T_post` |
| Control | `C_pre` | `C_post` |

It then calculates:

```text
treatment_growth = (T_post - T_pre) / T_pre
control_growth   = (C_post - C_pre) / C_pre
directional_gap  = treatment_growth - control_growth
```

The app calls `directional_gap` **estimated uplift**. This is **not the same quantity as additive difference-in-differences** `(T_post - T_pre) - (C_post - C_pre)` and is not a CATE model. Dividing by pre-period means also changes assumptions and interpretation.

## Original proof-of-concept revenue calculation

The supplied June 2026 prototype implements:

```text
illustrative_incremental_revenue = T_post × directional_gap × treated_post_days
reported_spend_ratio = illustrative_incremental_revenue / campaign_spend
```

**Interpretation warning:** This is a *directional scenario calculation*, not a counterfactual-based estimate of causal incremental revenue. Multiplying observed post-treatment revenue by a growth gap is not a generally justified incremental-revenue estimator, and the reported `ROI` ratio is not profit-based ROI.

If a future release adopts a **multiplicative-control-trend assumption**, the relevant counterfactual for average treated post-period revenue would instead be `T_pre × (C_post / C_pre)`, giving `(T_post - T_pre × C_post/C_pre) × treated_post_days`. This is a **different explicit identification assumption** and also requires appropriate adjustment for group sizes, time aggregation, and comparability. It should be implemented, tested, and documented before making any causal revenue claim.

## Confounding and identification

A relative pre/post gap alone cannot establish a causal effect. Stronger evaluation would require an actual randomized assignment or credible observational identification design, clarity about the observational unit, no interference, appropriate handling of changing demand, and pre-treatment trends/data checks. In particular, the synthetic example compares different customer segments, which should not be taken as randomized or interchangeable populations.

## Confidence and sensitivity

The UI uses simple rules to label findings High/Medium/Low based on row counts and detectable caveats. These are **not** calibrated confidence probabilities, statistical standard errors, p-values, confidence intervals, or formal sensitivity bounds. The sensitivity table perturbs the original uplift and spend inputs to illustrate fragility.

## Transparent scope

The PoC's strength is its inspectable formulas, explanations, and ability to respond to both positive and negative examples. A robust causal ML version is a separate future project requiring study design, statistical evaluation, and out-of-sample policy tests.
