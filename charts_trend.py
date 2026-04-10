"""
charts_trend.py — WoW & MoM bar charts untuk Show Up% dan Paid%
Dipakai di EC, CM, dan HO dashboard.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta

# ── Helper ────────────────────────────────────────────────────────────────────

def safe_pct(num, den):
    return round((num / den * 100), 1) if den > 0 else 0.0

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#1e1e2e", family="Inter"),
    margin=dict(l=10, r=10, t=50, b=60),
    yaxis=dict(gridcolor="rgba(0,0,0,0.04)", showline=False,
               tickformat=".0f", ticksuffix="%"),
)

def delta_label(current, previous):
    """Return delta string dan warna."""
    if previous == 0:
        return None, None
    diff = round(current - previous, 1)
    color = "#059669" if diff >= 0 else "#dc2626"
    sign  = "+" if diff >= 0 else ""
    return f"{sign}{diff}%", color


def make_bar_chart(labels, values, title, bar_color, show_delta_last=True):
    """Bar chart dengan label % dan delta di bar terakhir."""
    fig = go.Figure()

    colors = [bar_color] * len(values)

    fig.add_trace(go.Bar(
        x=list(range(len(labels))),
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#3d3d5c"),
        hovertemplate="<b>%{customdata}</b><br>%{y:.1f}%<extra></extra>",
        customdata=labels,
        cliponaxis=False,
    ))

    # Delta annotation di bar terakhir
    if show_delta_last and len(values) >= 2:
        delta_str, delta_color = delta_label(values[-1], values[-2])
        if delta_str:
            fig.add_annotation(
                x=len(labels) - 1,
                y=values[-1],
                text=f"<b>{delta_str}</b>",
                showarrow=False,
                yshift=32,
                font=dict(size=12, color=delta_color),
                bgcolor="white",
                bordercolor=delta_color,
                borderwidth=1,
                borderpad=3,
            )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font=dict(size=13, color="#3d3d5c"), x=0),
        yaxis_range=[0, max(values) * 1.4 if any(v > 0 for v in values) else 100],
        showlegend=False,
        height=320,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(labels))),
            ticktext=labels,
            tickangle=-30,
            tickfont=dict(size=10),
            gridcolor="rgba(0,0,0,0.04)",
            showline=False,
        ),
    )
    return fig


# ── WoW Chart ─────────────────────────────────────────────────────────────────

def build_wow_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agregat data per minggu.
    df harus punya kolom: tanggal, booking, show_up, paid
    """
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["week_start"] = df["tanggal"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = df.groupby("week_start").agg(
        booking=("booking", "sum"),
        show_up=("show_up", "sum"),
        paid=("paid", "sum"),
    ).reset_index()
    weekly["showup_pct"] = weekly.apply(lambda r: safe_pct(r["show_up"], r["booking"]), axis=1)
    weekly["paid_pct"]   = weekly.apply(lambda r: safe_pct(r["paid"], r["show_up"]), axis=1)
    weekly["label"] = weekly["week_start"].dt.strftime("W%V\n%d %b")
    return weekly.sort_values("week_start").tail(12)  # maks 12 minggu terakhir


def build_mom_data(df: pd.DataFrame) -> pd.DataFrame:
    """Agregat data per bulan."""
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["month"] = df["tanggal"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        booking=("booking", "sum"),
        show_up=("show_up", "sum"),
        paid=("paid", "sum"),
    ).reset_index()
    monthly["showup_pct"] = monthly.apply(lambda r: safe_pct(r["show_up"], r["booking"]), axis=1)
    monthly["paid_pct"]   = monthly.apply(lambda r: safe_pct(r["paid"], r["show_up"]), axis=1)
    monthly["label"] = monthly["month"].dt.strftime("%b %Y")
    return monthly.sort_values("month")


def show_trend_charts(df: pd.DataFrame, title_prefix: str = ""):
    """
    Tampilkan WoW dan MoM trend charts.
    df harus punya kolom: tanggal, booking, show_up, paid
    """
    if df.empty:
        st.info("Belum ada data untuk chart tren.")
        return

    st.markdown(f"""
    <h3 style='font-family:"Plus Jakarta Sans",sans-serif; font-size:0.95rem;
        font-weight:700; color:#3d3d5c; margin-bottom:0.5rem;'>
        📊 Tren Show Up % & Paid %{" — " + title_prefix if title_prefix else ""}
    </h3>""", unsafe_allow_html=True)

    view = st.radio(
        "Tampilan",
        ["Week on Week", "Month on Month"],
        horizontal=True,
        key=f"trend_view_{title_prefix}",
        label_visibility="collapsed",
    )

    if view == "Week on Week":
        data = build_wow_data(df)
        period_label = "Minggu"
    else:
        data = build_mom_data(df)
        period_label = "Bulan"

    if data.empty:
        st.info(f"Belum cukup data untuk chart {view}.")
        return

    labels      = data["label"].tolist()
    showup_vals = data["showup_pct"].tolist()
    paid_vals   = data["paid_pct"].tolist()

    col1, col2 = st.columns(2)
    with col1:
        fig1 = make_bar_chart(
            labels, showup_vals,
            f"Show Up % per {period_label}",
            "rgba(91,82,232,0.7)"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = make_bar_chart(
            labels, paid_vals,
            f"Paid % per {period_label}",
            "rgba(5,150,105,0.7)"
        )
        st.plotly_chart(fig2, use_container_width=True)
