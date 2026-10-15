"""app/ui.py – shared UI helpers: KPI cards, badges, chart wrappers, expanders.

Import this in every page:  from ui import kpi_card, caveat_badge, sql_expander
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


# ─── Colour palette ───────────────────────────────────────────────────────────
ORANGE = "#E06B3F"
BLUE   = "#2E86AB"
GREEN  = "#3DAA77"
RED    = "#C0392B"
GREY   = "#95A5A6"
BG     = "#F4F6FA"

PALETTE = [ORANGE, BLUE, GREEN, RED, GREY, "#8E44AD", "#F39C12", "#1ABC9C"]


# ─── KPI card ─────────────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, delta: str = "", n: str = "", help: str = ""):
    """Render a single KPI metric block."""
    st.metric(label=label, value=value, delta=delta or None, help=help or None)
    if n:
        st.caption(f"n = {n}")


def kpi_row(cards: list[dict]):
    """Render a row of KPI cards from a list of dicts with keys label/value/delta/n/help."""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            kpi_card(**card)


# ─── Badges ───────────────────────────────────────────────────────────────────

def caveat_badge(msg: str = "Exploratory · not causal · association only"):
    st.caption(f"⚠️ {msg}")


def small_n_badge(n: int, threshold: int = 100):
    if n < threshold:
        st.caption(f"⚠️ Small sample (n = {n} < {threshold}): interpret with caution.")


def exploratory_note():
    st.info(
        "🔬 **Exploratory:** these comparisons are observational. "
        "Say 'associated with', not 'caused by'. No multiple-comparison correction applied.",
        icon=None,
    )


# ─── SQL / method expander ────────────────────────────────────────────────────

from pathlib import Path as _Path

_SQL_DIR = _Path(__file__).resolve().parent.parent / "sql"


def sql_expander(title: str, sql_or_method: str):
    """Pass a file name such as '04_funnel.sql' to show the REAL SQL that produced the numbers.
    Any other string is shown as plain method text (never retyped SQL)."""
    with st.expander(f"📐 Show method / SQL — {title}"):
        f = _SQL_DIR / sql_or_method
        if sql_or_method.endswith(".sql") and f.exists():
            st.caption(f"Actual file: sql/{sql_or_method}")
            st.code(f.read_text(encoding="utf-8"), language="sql")
        else:
            st.markdown(sql_or_method)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% interval for a proportion k/n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (c - h, c + h)


def method_expander(title: str, text: str):
    with st.expander(f"📐 Show method — {title}"):
        st.markdown(text)


# ─── Section header ───────────────────────────────────────────────────────────

def section(title: str, subtitle: str = ""):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


# ─── Filter-not-applied label ─────────────────────────────────────────────────

def precomputed_label():
    st.caption("📊 Full window (sidebar filters not applied to this pre-computed table)")


# ─── Empty-state guard ────────────────────────────────────────────────────────

def empty_state_guard(df, min_rows: int = 1, msg: str = "No data for the selected filters. Widen your selection.") -> bool:
    """Returns True if data is sufficient, False (and shows warning) if not."""
    if df is None or len(df) < min_rows:
        st.warning(msg)
        return False
    return True


# ─── Download buttons ─────────────────────────────────────────────────────────

def download_csv(df, label: str = "Download CSV", filename: str = "data.csv"):
    st.download_button(
        label=f"⬇️ {label}",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def download_brief(text: str, label: str = "Download Executive Brief (Markdown)", filename: str = "executive_brief.md"):
    st.download_button(
        label=f"⬇️ {label}",
        data=text.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
    )


# ─── Waterfall chart helper ───────────────────────────────────────────────────

def waterfall_chart(labels: list[str], values: list[float], title: str = "") -> go.Figure:
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] * len(labels),
        x=labels,
        y=values,
        connector={"line": {"color": GREY}},
        decreasing={"marker": {"color": RED}},
        increasing={"marker": {"color": GREEN}},
        totals={"marker": {"color": ORANGE}},
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        showlegend=False,
        plot_bgcolor=BG,
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ─── CI bar chart helper ──────────────────────────────────────────────────────

def ci_bar_chart(
    df, x_col: str, y_col: str, lo_col: str, hi_col: str,
    title: str = "", xlabel: str = "", ylabel: str = "",
    color: str = ORANGE,
) -> go.Figure:
    error_y = dict(
        type="data",
        symmetric=False,
        array=(df[hi_col] - df[y_col]).tolist(),
        arrayminus=(df[y_col] - df[lo_col]).tolist(),
    )
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col], error_y=error_y,
        marker_color=color, text=df[y_col].round(3), textposition="outside",
    ))
    fig.update_layout(
        title=title, xaxis_title=xlabel, yaxis_title=ylabel,
        plot_bgcolor=BG, paper_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
