from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

REQUIRED_COLUMNS = ["date", "group", "period", "revenue", "ad_spend", "campaign_flag"]
OPTIONAL_COLUMNS = [
    "product_category",
    "segment",
    "sessions",
    "conversion_rate",
    "channel",
    "discount_flag",
    "stock_status",
    "notes",
]


@dataclass
class AnalysisResult:
    treatment_pre_avg: float
    treatment_post_avg: float
    control_pre_avg: float
    control_post_avg: float
    treatment_growth: float
    control_growth: float
    estimated_uplift: float
    incremental_revenue: float
    campaign_spend: float
    estimated_roi: Optional[float]
    confidence: str
    caveats: List[str]
    next_action: str
    n_post_days: int


# ---------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------


def build_positive_demo_data() -> pd.DataFrame:
    """Create deterministic positive-but-caveated campaign data."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-06-01", periods=28, freq="D")
    rows = []

    for dt in dates:
        is_post = dt >= pd.Timestamp("2026-06-15")

        for group in ["treatment", "control"]:
            period = "post" if is_post else "pre"
            campaign_flag = 1 if (is_post and group == "treatment") else 0

            base_sessions = 1180 if group == "treatment" else 1130
            sessions = int(max(850, base_sessions + rng.normal(0, 55)))

            if group == "treatment":
                base_cr = 0.031 if not is_post else 0.038
                base_aov = 102 if not is_post else 108
                ad_spend = float(max(0, rng.normal(410, 35))) if is_post else 0.0
                discount_flag = 1 if is_post and dt.day in [15, 16, 17, 18] else 0
                channel = "Email"
                notes = (
                    "abandoned cart campaign active" if is_post else "baseline period"
                )
                segment = "Returning Customers"
            else:
                base_cr = 0.030 if not is_post else 0.032
                base_aov = 101 if not is_post else 103
                ad_spend = 0.0
                discount_flag = 1 if is_post and dt.day in [15, 16, 17, 18] else 0
                channel = "None"
                notes = "control segment no campaign" if is_post else "baseline period"
                segment = "New Customers"

            cr = max(0.005, base_cr + rng.normal(0, 0.002))
            revenue = float(sessions * cr * base_aov + rng.normal(0, 140))
            revenue = max(revenue, 0)

            rows.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "product_category": "Skincare",
                    "segment": segment,
                    "group": group,
                    "period": period,
                    "sessions": sessions,
                    "conversion_rate": round(cr, 4),
                    "revenue": round(revenue, 2),
                    "ad_spend": round(ad_spend, 2),
                    "campaign_flag": campaign_flag,
                    "channel": channel,
                    "discount_flag": discount_flag,
                    "stock_status": "normal",
                    "notes": notes,
                }
            )

    return pd.DataFrame(rows)


def build_negative_demo_data() -> pd.DataFrame:
    """Create deterministic negative-uplift campaign data.

    The treatment group receives a campaign but underperforms against the control group.
    This proves the app does not always produce optimistic recommendations.
    """
    rng = np.random.default_rng(91)
    dates = pd.date_range("2026-06-01", periods=28, freq="D")
    rows = []

    for dt in dates:
        is_post = dt >= pd.Timestamp("2026-06-15")

        for group in ["treatment", "control"]:
            period = "post" if is_post else "pre"
            campaign_flag = 1 if (is_post and group == "treatment") else 0

            base_sessions = 1160 if group == "treatment" else 1140
            sessions = int(max(850, base_sessions + rng.normal(0, 45)))

            if group == "treatment":
                # Treatment looks worse after launch: weaker CR and slight AOV drop.
                base_cr = 0.032 if not is_post else 0.028
                base_aov = 104 if not is_post else 101
                ad_spend = float(max(0, rng.normal(430, 30))) if is_post else 0.0
                discount_flag = 0
                channel = "Email"
                notes = (
                    "campaign active but weak offer/message fit"
                    if is_post
                    else "baseline period"
                )
                segment = "Returning Customers"
            else:
                # Control improves naturally.
                base_cr = 0.031 if not is_post else 0.034
                base_aov = 103 if not is_post else 105
                ad_spend = 0.0
                discount_flag = 0
                channel = "None"
                notes = "control segment no campaign" if is_post else "baseline period"
                segment = "New Customers"

            cr = max(0.005, base_cr + rng.normal(0, 0.0015))
            revenue = float(sessions * cr * base_aov + rng.normal(0, 110))
            revenue = max(revenue, 0)

            rows.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "product_category": "Skincare",
                    "segment": segment,
                    "group": group,
                    "period": period,
                    "sessions": sessions,
                    "conversion_rate": round(cr, 4),
                    "revenue": round(revenue, 2),
                    "ad_spend": round(ad_spend, 2),
                    "campaign_flag": campaign_flag,
                    "channel": channel,
                    "discount_flag": discount_flag,
                    "stock_status": "normal",
                    "notes": notes,
                }
            )

    return pd.DataFrame(rows)


# Backward-compatible alias.
def build_demo_data() -> pd.DataFrame:
    return build_positive_demo_data()


# ---------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def coerce_bool_like(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["1", "true", "yes", "y", "active", "on"])
    )


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    try:
        return pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="latin-1")


def validate_and_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    df = normalize_columns(df)
    errors = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return df, errors

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        errors.append("Some date values could not be parsed.")

    for col in ["revenue", "ad_spend", "sessions", "conversion_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["revenue"].isna().any():
        errors.append("Some revenue values are missing or non-numeric.")
    if df["ad_spend"].isna().any():
        errors.append("Some ad_spend values are missing or non-numeric.")

    df["group"] = df["group"].astype(str).str.strip().str.lower()
    df["period"] = df["period"].astype(str).str.strip().str.lower()

    valid_groups = {"treatment", "control"}
    valid_periods = {"pre", "post"}

    if not set(df["group"].dropna()).issubset(valid_groups):
        errors.append("Column 'group' must only contain treatment or control.")
    if not set(df["period"].dropna()).issubset(valid_periods):
        errors.append("Column 'period' must only contain pre or post.")

    df["campaign_flag_bool"] = coerce_bool_like(df["campaign_flag"])

    if "discount_flag" in df.columns:
        df["discount_flag_bool"] = coerce_bool_like(df["discount_flag"])

    combos = set(zip(df["group"], df["period"]))
    needed = {
        ("treatment", "pre"),
        ("treatment", "post"),
        ("control", "pre"),
        ("control", "post"),
    }
    missing_combos = needed - combos
    if missing_combos:
        missing_text = ", ".join([f"{g}/{p}" for g, p in sorted(missing_combos)])
        errors.append(f"Missing required group-period combinations: {missing_text}")

    return df, errors


# ---------------------------------------------------------------------
# Analysis logic
# ---------------------------------------------------------------------


def safe_growth(post: float, pre: float) -> float:
    if pre == 0 or pd.isna(pre):
        return np.nan
    return (post - pre) / pre


def build_caveats(df: pd.DataFrame) -> List[str]:
    caveats = []
    post_df = df[df["period"] == "post"]

    if len(df) < 12:
        caveats.append("Small dataset: fewer than 12 rows. Confidence is reduced.")

    if "discount_flag_bool" in df.columns and post_df["discount_flag_bool"].any():
        caveats.append(
            "Discount active in post period: discount may bias revenue upward."
        )

    if "stock_status" in df.columns:
        stock_text = post_df["stock_status"].astype(str).str.lower()
        if stock_text.str.contains("low|stockout", regex=True, na=False).any():
            caveats.append(
                "Stock effects detected: low stock or stockout may distort revenue."
            )

    if "sessions" in df.columns and post_df["sessions"].notna().any():
        sessions_by_group = post_df.groupby("group")["sessions"].mean()
        if {"treatment", "control"}.issubset(set(sessions_by_group.index)):
            treatment_sessions = sessions_by_group.get("treatment", np.nan)
            control_sessions = sessions_by_group.get("control", np.nan)
            denom = max(abs(control_sessions), 1)
            diff_ratio = abs(treatment_sessions - control_sessions) / denom
            if diff_ratio > 0.30:
                caveats.append(
                    f"Traffic imbalance: treatment/control post-period sessions differ by ~{diff_ratio:.0%}."
                )

    if "channel" in df.columns and "campaign_flag_bool" in df.columns:
        active_channels = (
            post_df[post_df["campaign_flag_bool"]]["channel"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", np.nan)
            .dropna()
            .unique()
        )
        if len(active_channels) > 1:
            caveats.append(
                "Campaign overlap: campaign_flag is active across multiple channels, making attribution less clean."
            )

    return caveats


def estimate_confidence(df: pd.DataFrame, caveats: List[str]) -> str:
    """Simple transparent confidence scoring.

    High: required data present, enough rows, no major confounders.
    Medium: usable data but one or two caveats / modestly small dataset.
    Low: too few rows, many confounders, or material data quality risk.
    """
    score = 3

    if len(df) < 8:
        score -= 2
    elif len(df) < 12:
        score -= 1

    n_caveats = len(caveats)
    if n_caveats >= 3:
        score -= 2
    elif n_caveats >= 1:
        score -= 1

    if score >= 3:
        return "High"
    if score == 2:
        return "Medium"
    return "Low"


def analyze_campaign(df: pd.DataFrame) -> AnalysisResult:
    summary = (
        df.groupby(["group", "period"], dropna=False)["revenue"]
        .mean()
        .unstack("period")
    )

    treatment_pre = float(summary.loc["treatment", "pre"])
    treatment_post = float(summary.loc["treatment", "post"])
    control_pre = float(summary.loc["control", "pre"])
    control_post = float(summary.loc["control", "post"])

    treatment_growth = safe_growth(treatment_post, treatment_pre)
    control_growth = safe_growth(control_post, control_pre)
    estimated_uplift = treatment_growth - control_growth

    # Simple directional total-period estimate.
    daily_incremental_revenue = treatment_post * estimated_uplift

    treatment_post_df = df[(df["group"] == "treatment") & (df["period"] == "post")]
    n_post_days = int(treatment_post_df["date"].nunique())

    spend_df = treatment_post_df[treatment_post_df["campaign_flag_bool"]]
    campaign_spend = float(spend_df["ad_spend"].sum())

    total_incremental_revenue = daily_incremental_revenue * n_post_days

    estimated_roi = None
    if (
        campaign_spend > 0
        and not pd.isna(total_incremental_revenue)
        and n_post_days > 0
    ):
        estimated_roi = total_incremental_revenue / campaign_spend

    caveats = build_caveats(df)
    confidence = estimate_confidence(df, caveats)

    if pd.isna(estimated_uplift):
        next_action = (
            "Data quality issue: fix pre/post revenue inputs before making a decision."
        )
    elif estimated_uplift > 0.02 and confidence == "High":
        next_action = (
            "Positive signal with high confidence. Scale gradually, keep the control group "
            "active, and monitor ROI before committing larger budget increases."
        )
    elif estimated_uplift > 0.02 and confidence == "Medium":
        next_action = (
            "Promising directional signal but confidence is only moderate. "
            "Re-test with a cleaner control group or scale cautiously (e.g. +10–20% budget)."
        )
    elif estimated_uplift > 0.02:
        next_action = (
            "Positive directional signal, but confidence is low. "
            "Improve test design before scaling the campaign."
        )
    elif estimated_uplift >= -0.02:
        next_action = (
            "Estimated uplift is near zero. Hold or redesign the campaign, "
            "inspect confounders, and run a cleaner test before committing more budget."
        )
    else:
        next_action = (
            "Estimated uplift is negative. Pause or revise the campaign, "
            "review confounders, and re-test with a stronger hypothesis."
        )

    return AnalysisResult(
        treatment_pre_avg=treatment_pre,
        treatment_post_avg=treatment_post,
        control_pre_avg=control_pre,
        control_post_avg=control_post,
        treatment_growth=treatment_growth,
        control_growth=control_growth,
        estimated_uplift=estimated_uplift,
        incremental_revenue=total_incremental_revenue,
        campaign_spend=campaign_spend,
        estimated_roi=estimated_roi,
        confidence=confidence,
        caveats=caveats,
        next_action=next_action,
        n_post_days=n_post_days,
    )


# ---------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------


def fmt_currency(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def fmt_pct(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.1%}"


def fmt_pp(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value * 100:+.1f} percentage points"


def fmt_roi(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}x"


def confidence_badge(confidence: str) -> str:
    colors = {"High": "#DCFCE7", "Medium": "#FEF3C7", "Low": "#FEE2E2"}
    text_colors = {"High": "#166534", "Medium": "#92400E", "Low": "#991B1B"}
    bg = colors.get(confidence, "#E5E7EB")
    fg = text_colors.get(confidence, "#111827")
    return f"""
    <div style="background:{bg}; color:{fg}; padding:0.65rem 0.9rem; border-radius:0.75rem; font-weight:700; display:inline-block;">
        Confidence: {confidence}
    </div>
    """


# ---------------------------------------------------------------------
# Explainability logic
# ---------------------------------------------------------------------


def render_summary(result: AnalysisResult) -> str:
    roi_text = fmt_roi(result.estimated_roi)
    return (
        f"The treatment group revenue changed by {fmt_pct(result.treatment_growth)}, while the control group changed by "
        f"{fmt_pct(result.control_growth)}. The directional uplift estimate is {fmt_pp(result.estimated_uplift)}. "
        f"Estimated incremental revenue is {fmt_currency(result.incremental_revenue)}, with estimated ROI of {roi_text}. "
        f"This is directional decision support, not definitive causal proof."
    )


def build_formula_trace(result: AnalysisResult) -> Dict[str, str]:
    return {
        "Treatment pre avg revenue": fmt_currency(result.treatment_pre_avg),
        "Treatment post avg revenue": fmt_currency(result.treatment_post_avg),
        "Treatment growth": fmt_pct(result.treatment_growth),
        "Control pre avg revenue": fmt_currency(result.control_pre_avg),
        "Control post avg revenue": fmt_currency(result.control_post_avg),
        "Control growth": fmt_pct(result.control_growth),
        "Estimated uplift": fmt_pp(result.estimated_uplift),
        "Incremental revenue formula": "Treatment post avg revenue × estimated uplift × post-period days",
        "Incremental revenue": fmt_currency(result.incremental_revenue),
        "ROI formula": "Total incremental revenue / campaign spend",
        "Estimated ROI": fmt_roi(result.estimated_roi),
    }


def explain_confidence(
    df: pd.DataFrame, caveats: List[str], confidence: str
) -> List[str]:
    reasons = [
        "Required treatment/control and pre/post groups are present.",
        "Revenue and ad_spend fields are numeric and usable after validation.",
    ]

    if len(df) >= 12:
        reasons.append("Dataset size is usable for a lightweight directional analysis.")
    elif len(df) >= 8:
        reasons.append("Dataset is modestly small, so confidence is reduced.")
    else:
        reasons.append("Dataset is very small, so confidence is low.")

    if caveats:
        reasons.append(f"{len(caveats)} caveat(s) were detected, reducing confidence.")
        reasons.extend(caveats)
    else:
        reasons.append(
            "No major confounder warnings were detected from available columns."
        )

    reasons.append(f"Final confidence level: {confidence}.")
    return reasons


def explain_recommendation(result: AnalysisResult) -> List[str]:
    reasons = []

    if pd.isna(result.estimated_uplift):
        return [
            "Uplift could not be calculated, so the system recommends fixing data quality first."
        ]

    if result.estimated_uplift > 0.02:
        reasons.append(
            "Estimated uplift is positive and above the +2% decision threshold."
        )
    elif result.estimated_uplift >= -0.02:
        reasons.append(
            "Estimated uplift is near zero, so the campaign does not show a strong directional effect."
        )
    else:
        reasons.append(
            "Estimated uplift is negative, so the campaign underperformed the control group directionally."
        )

    if result.estimated_roi is not None:
        if result.estimated_roi >= 1:
            reasons.append("Estimated ROI is above 1.0x relative to campaign spend.")
        elif result.estimated_roi >= 0:
            reasons.append(
                "Estimated ROI is positive but below 1.0x, so spend efficiency is weak."
            )
        else:
            reasons.append(
                "Estimated ROI is negative, so the campaign likely destroyed value during the test window."
            )
    else:
        reasons.append(
            "ROI could not be calculated because campaign spend is zero or unavailable."
        )

    if result.confidence == "High":
        reasons.append("Confidence is high, so cautious scaling can be considered.")
    elif result.confidence == "Medium":
        reasons.append(
            "Confidence is medium, so the system recommends cautious scaling or retesting rather than aggressive scaling."
        )
    else:
        reasons.append(
            "Confidence is low, so the system recommends improving test design before scaling."
        )

    if result.caveats:
        reasons.append(
            "Detected caveats should be reviewed before acting on the recommendation."
        )

    return reasons


def run_sensitivity_checks(result: AnalysisResult) -> Dict[str, str]:
    if (
        result.estimated_roi is None
        or result.campaign_spend <= 0
        or result.n_post_days <= 0
    ):
        return {
            "Sensitivity unavailable": "ROI sensitivity requires positive campaign spend and post-period data."
        }

    post_avg = result.treatment_post_avg
    days = result.n_post_days
    spend = result.campaign_spend

    uplift_minus_5pp = result.estimated_uplift - 0.05
    revenue_minus_5pp = post_avg * uplift_minus_5pp * days
    roi_minus_5pp = revenue_minus_5pp / spend

    spend_plus_25 = spend * 1.25
    roi_spend_plus_25 = result.incremental_revenue / spend_plus_25

    half_uplift = result.estimated_uplift * 0.5
    revenue_half_uplift = post_avg * half_uplift * days
    roi_half_uplift = revenue_half_uplift / spend

    return {
        "If uplift is 5 percentage points lower": f"Estimated ROI becomes {fmt_roi(roi_minus_5pp)}.",
        "If campaign spend is 25% higher": f"Estimated ROI becomes {fmt_roi(roi_spend_plus_25)}.",
        "If only half the uplift is real": f"Estimated ROI becomes {fmt_roi(roi_half_uplift)}.",
    }


def build_decision_card(result: AnalysisResult) -> str:
    rationale_text = "\n".join([f"- {r}" for r in explain_recommendation(result)])
    caveat_text = (
        "\n".join([f"- {c}" for c in result.caveats])
        if result.caveats
        else "- No major caveats detected."
    )
    sensitivity_text = "\n".join(
        [f"- {k}: {v}" for k, v in run_sensitivity_checks(result).items()]
    )

    return f"""
**Decision:** {result.next_action}

**Estimated uplift:** {fmt_pp(result.estimated_uplift)}  
**Incremental revenue:** {fmt_currency(result.incremental_revenue)}  
**Campaign spend:** {fmt_currency(result.campaign_spend)}  
**Estimated ROI:** {fmt_roi(result.estimated_roi)}  
**Confidence:** {result.confidence}

**Why this recommendation?**  
{rationale_text}

**Main caveats:**  
{caveat_text}

**Sensitivity checks:**  
{sensitivity_text}

**Important limitation:** This is directional decision support, not definitive causal proof.
"""


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="Explainable Causal Campaign Analyst Agent",
        page_icon="📈",
        layout="wide",
    )

    st.title("Explainable Causal Campaign Analyst Agent")
    st.caption(
        "A lightweight Enrich Labs PoC: from campaign execution to explainable campaign learning."
    )

    st.info(
        "This app provides directional decision support, not definitive causal proof. "
        "Calculations are deterministic Python/pandas outputs, not LLM-generated numbers."
    )

    positive_demo_df = build_positive_demo_data()
    negative_demo_df = build_negative_demo_data()

    with st.sidebar:
        st.header("Data input")
        uploaded = st.file_uploader("Upload campaign CSV", type=["csv"])

        st.markdown("### Demo datasets")
        use_positive_demo = st.button(
            "Use positive demo dataset", use_container_width=True
        )
        use_negative_demo = st.button(
            "Use negative demo dataset", use_container_width=True
        )

        st.divider()
        st.download_button(
            "Download positive sample CSV",
            data=positive_demo_df.to_csv(index=False).encode("utf-8"),
            file_name="sample_campaign_data_positive.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download negative sample CSV",
            data=negative_demo_df.to_csv(index=False).encode("utf-8"),
            file_name="sample_campaign_data_negative.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.caption(
            "Required columns: date, group, period, revenue, ad_spend, campaign_flag."
        )
        st.caption(
            "Optional columns improve caveat detection: sessions, discount_flag, stock_status, channel, notes."
        )

    if use_positive_demo:
        raw_df = positive_demo_df
        st.session_state["selected_dataset"] = "positive"
        data_label = "Positive demo dataset"
    elif use_negative_demo:
        raw_df = negative_demo_df
        st.session_state["selected_dataset"] = "negative"
        data_label = "Negative demo dataset"
    elif uploaded is not None:
        raw_df = load_uploaded_csv(uploaded)
        st.session_state["selected_dataset"] = "uploaded"
        data_label = "Uploaded CSV"
    else:
        selected = st.session_state.get("selected_dataset", "positive")
        if selected == "negative":
            raw_df = negative_demo_df
            data_label = "Negative demo dataset"
        else:
            raw_df = positive_demo_df
            data_label = "Positive demo dataset"

    df, errors = validate_and_clean(raw_df)

    st.subheader("1. Data preview")
    st.caption(f"Source: {data_label}")
    st.dataframe(df.head(30), use_container_width=True)

    if errors:
        st.error("Please fix the following input issues before analysis:")
        for err in errors:
            st.write(f"- {err}")
        st.stop()

    result = analyze_campaign(df)

    st.subheader("2. Executive summary")
    st.write(render_summary(result))
    st.markdown(confidence_badge(result.confidence), unsafe_allow_html=True)

    st.subheader("3. KPI cards")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated uplift", fmt_pp(result.estimated_uplift))
    c2.metric("Incremental revenue", fmt_currency(result.incremental_revenue))
    c3.metric("Campaign spend", fmt_currency(result.campaign_spend))
    c4.metric("Estimated ROI", fmt_roi(result.estimated_roi))

    st.caption(
        "Formula: uplift = treatment growth − control growth; "
        "total incremental revenue = treatment post avg revenue × uplift × post-period days; "
        "ROI = total incremental revenue / campaign spend."
    )

    st.subheader("4. Pre/post revenue chart")
    line_df = df.sort_values("date")
    fig_line = px.line(
        line_df,
        x="date",
        y="revenue",
        color="group",
        markers=True,
        title="Revenue trend by group",
        labels={"date": "Date", "revenue": "Revenue", "group": "Group"},
    )
    post_dates = df.loc[df["period"] == "post", "date"]
    if not post_dates.empty:
        campaign_start = post_dates.min()
        # Use an explicit shape and annotation: Plotly's add_vline with a
        # pandas Timestamp plus annotation_text can fail on recent pandas.
        fig_line.add_shape(
            type="line", x0=campaign_start, x1=campaign_start,
            y0=0, y1=1, yref="paper",
            line=dict(color="#64748b", width=1.5, dash="dash"),
        )
        fig_line.add_annotation(
            x=campaign_start, y=1, yref="paper", text="Post period starts",
            showarrow=False, yshift=17, font=dict(size=11, color="#64748b"),
        )
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("5. Treatment vs control comparison")
    bar_df = (
        df.groupby(["group", "period"], as_index=False)["revenue"]
        .mean()
        .rename(columns={"revenue": "avg_revenue"})
    )
    fig_bar = px.bar(
        bar_df,
        x="group",
        y="avg_revenue",
        color="period",
        barmode="group",
        title="Average revenue by group and period",
        labels={"group": "Group", "avg_revenue": "Average revenue", "period": "Period"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("6. Caveats and confounders")
    if result.caveats:
        for caveat in result.caveats:
            st.warning(caveat)
    else:
        st.success("No major confounder warnings detected from the available columns.")

    with st.expander("Show calculation details"):
        calc_df = pd.DataFrame(
            [
                ["Treatment pre avg revenue", result.treatment_pre_avg],
                ["Treatment post avg revenue", result.treatment_post_avg],
                ["Control pre avg revenue", result.control_pre_avg],
                ["Control post avg revenue", result.control_post_avg],
                ["Post-period days", result.n_post_days],
                ["Treatment growth", result.treatment_growth],
                ["Control growth", result.control_growth],
                ["Estimated uplift", result.estimated_uplift],
                ["Total incremental revenue", result.incremental_revenue],
                ["Campaign spend", result.campaign_spend],
                [
                    "Estimated ROI",
                    result.estimated_roi
                    if result.estimated_roi is not None
                    else np.nan,
                ],
            ],
            columns=["metric", "value"],
        )
        st.dataframe(calc_df, use_container_width=True)

    st.subheader("7. Explainability layer")
    st.markdown(
        "This layer makes the recommendation inspectable: formula path, confidence drivers, rationale, and sensitivity."
    )

    st.markdown("#### Formula trace")
    formula_df = pd.DataFrame(
        list(build_formula_trace(result).items()),
        columns=["Item", "Explanation"],
    )
    st.dataframe(formula_df, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Confidence explanation")
        for reason in explain_confidence(df, result.caveats, result.confidence):
            st.write(f"- {reason}")

    with col_b:
        st.markdown("#### Recommendation rationale")
        for reason in explain_recommendation(result):
            st.write(f"- {reason}")

    st.markdown("#### Sensitivity checks")
    sensitivity_df = pd.DataFrame(
        list(run_sensitivity_checks(result).items()),
        columns=["Scenario", "Result"],
    )
    st.dataframe(sensitivity_df, use_container_width=True)

    with st.expander("Explainable decision card"):
        st.markdown(build_decision_card(result))

    st.subheader("8. Recommended next action")
    if result.estimated_uplift < -0.02:
        st.error(result.next_action)
    elif result.estimated_uplift >= -0.02 and result.estimated_uplift <= 0.02:
        st.warning(result.next_action)
    else:
        st.success(result.next_action)

    st.divider()

    with st.expander("Methodology"):
        st.markdown(
            """
This app uses a simple **difference-in-differences style comparison**:

1. **Pre-period baseline**: average daily revenue is calculated for both the treatment
   group (received the campaign) and the control group (did not).
2. **Post-period outcome**: the same averages are calculated for the period after the
   campaign started.
3. **Growth rates**: the percentage change from pre to post is computed for each group.
4. **Uplift estimate**: the control group's growth is subtracted from the treatment
   group's growth — the remainder is the estimated campaign effect.
5. **Incremental revenue**: the treatment group's post-period average daily revenue is
   multiplied by the estimated uplift rate and by the number of post-period days, so the result
   represents the total incremental revenue over the campaign window.
6. **Estimated ROI**: total incremental revenue divided by total campaign spend (`ad_spend`).
7. **Explainability**: formula trace, confidence reasons, recommendation rationale,
   and sensitivity checks are shown so the user can inspect the decision logic.

No machine learning, no LLM, no black-box causal inference library — every number
is a deterministic Python/pandas calculation you can inspect in the calculation details.
            """
        )

    with st.expander("Limitations"):
        st.markdown(
            """
- This is **directional decision support, not definitive causal proof**.
- The method assumes the treatment and control groups were comparable before the campaign
  (parallel trends). If they were already trending differently, the uplift estimate is biased.
- Results can be distorted by discounts, seasonality, stock issues, overlapping campaigns,
  and traffic imbalance between groups.
- The confidence score is a heuristic, not a statistical significance test.
- Sensitivity checks are simple scenario tests, not full uncertainty intervals.
- A production version would need:
  - Live connectors to Shopify, Klaviyo, Google Ads, Meta Ads, TikTok, and Google Analytics
  - Proper A/B test randomization and sample-size planning
  - Statistical significance tests where appropriate
  - Audit logs, permission controls, recurring scheduled reports, and rollback
  - Explainability logs for every recommendation
- This PoC is designed to demonstrate the **concept** of campaign learning —
  moving from "we ran a campaign" to "we estimated what the campaign changed and why we recommend the next action."
            """
        )

    st.divider()
    st.caption(
        "Built for the Enrich Labs case study. This PoC shows a practical path from marketing execution to explainable campaign learning."
    )


if __name__ == "__main__":
    main()
