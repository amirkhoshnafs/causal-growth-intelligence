# Limitations and next steps

## Known limitations in this supplied prototype

1. **Not identified causal impact.** Differences in observed treatment/control growth can reflect preexisting trends and other business changes.
2. **Revenue counterfactual.** The included illustrative formula `T_post × growth_gap` is not a generally valid causal incremental-revenue estimator; see `methodology.md`.
3. **ROI semantics.** Revenue/spend is not incremental *profit* ROI. Costs, margins, returns, and uncertainty are not modeled.
4. **Heuristic confidence.** The High/Medium/Low indicator is based on row counts and warnings, not inference.
5. **Synthetic cohort comparability.** Positive/negative demos use distinct customer segments for treatment and control; parallel trends are not established.
6. **Unverified production integration.** CSV-only input, no external API connections, no automated executions, no audit database.
7. **Aggregation grain.** Mean-over-row revenue and unique-day scaling assume a consistent observational unit and coverage; multi-row uploads require extra care.
8. **Experiment validity.** No power analysis, pre-trend diagnostics, propensity controls, uncertainty quantification, or policy-value evaluation.

## Prioritized improvements for a later methodological release

- Define a clear estimand and units (e.g., incremental revenue per eligible customer vs. store/day).
- Use randomized holdouts where possible, or choose and justify an observational design.
- Replace the PoC revenue calculation with an explicitly identified estimator and synthetic verification tests.
- Report uncertainty and realistic decision thresholds; never turn heuristic warnings into statistical confidence.
- Add business-unit economics (incremental *profit* and spend) and a correct iROAS/ROI distinction.
- Add unit-of-analysis validation, group/date aggregation, missingness and treatment contamination checks.
- Only afterward add richer estimators (T/X/R/DR learners), CATE, capacity-constrained policy evaluation and connectors.

The project is still suitable as a documented **product engineering and explainable decision-support PoC**, provided these boundaries are visible to readers.
