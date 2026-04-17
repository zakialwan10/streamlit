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
    """Agregat data per minggu, hanya sampai hari ini."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df = df.dropna(subset=["tanggal"])
    today = pd.Timestamp.now().normalize()
    df = df[df["tanggal"] <= today]
    if df.empty:
        return pd.DataFrame()
    df["week_start"] = df["tanggal"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = df.groupby("week_start").agg(
        booking=("booking", "sum"),
        show_up=("show_up", "sum"),
        paid=("paid", "sum"),
    ).reset_index()
    weekly["showup_pct"] = weekly.apply(
        lambda r: round(r["show_up"] / r["booking"] * 100, 1) if r["booking"] > 0 else 0.0,
        axis=1
    )
    weekly["paid_pct"] = weekly.apply(
        lambda r: round(r["paid"] / r["show_up"] * 100, 1) if r["show_up"] > 0 else 0.0,
        axis=1
    )
    weekly["label"] = weekly["week_start"].dt.strftime("W%V\n%d %b")
    # Filter hanya minggu yang ada datanya, lalu ambil 12 terakhir
    weekly = weekly[weekly["booking"] > 0]
    return weekly.sort_values("week_start").tail(12).reset_index(drop=True)


def build_mom_data(df: pd.DataFrame) -> pd.DataFrame:
    """Agregat data per bulan, hanya sampai hari ini."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df = df.dropna(subset=["tanggal"])
    today = pd.Timestamp.now().normalize()
    df = df[df["tanggal"] <= today]
    if df.empty:
        return pd.DataFrame()
    df["month"] = df["tanggal"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        booking=("booking", "sum"),
        show_up=("show_up", "sum"),
        paid=("paid", "sum"),
    ).reset_index()
    monthly["showup_pct"] = monthly.apply(
        lambda r: round(r["show_up"] / r["booking"] * 100, 1) if r["booking"] > 0 else 0.0,
        axis=1
    )
    monthly["paid_pct"] = monthly.apply(
        lambda r: round(r["paid"] / r["show_up"] * 100, 1) if r["show_up"] > 0 else 0.0,
        axis=1
    )
    monthly["label"] = monthly["month"].dt.strftime("%b %Y")
    # Filter hanya bulan yang ada datanya
    monthly = monthly[monthly["booking"] > 0]
    return monthly.sort_values("month").reset_index(drop=True)


def show_trend_charts(df: pd.DataFrame, title_prefix: str = "", centers: list = None):
    """
    Tampilkan WoW dan MoM trend charts.
    - Jika centers diberikan (list center atau None=semua): ambil dari wow_mom_data sheet
    - Jika centers="ec" (per EC individual): hitung dari df harian
    df harus punya kolom: tanggal, booking, show_up, paid (dipakai hanya jika centers="ec")
    """
    use_loader = (centers != "ec")  # pakai wow_mom_data kecuali untuk per-EC

    if use_loader:
        # Ambil data dari wow_mom_data
        from wow_mom_loader import get_trend_data, CENTER_ROWS
        actual_centers = centers if centers is not None else list(CENTER_ROWS.keys())
        trend_data = get_trend_data(actual_centers)
        has_data = bool(trend_data) and (
            not trend_data.get("mom", pd.DataFrame()).empty or
            not trend_data.get("wow", pd.DataFrame()).empty
        )
        if not has_data:
            st.info("Belum ada data tren untuk center yang dipilih.")
            return
    else:
        if df is None or df.empty:
            st.info("Belum ada data untuk chart tren.")
            return

    st.markdown(f"""
    <div style='background:#ffffff; border:1px solid #dde0f0; border-radius:16px;
        padding:1.2rem 1.5rem; margin-bottom:1rem;
        box-shadow: 0 2px 8px rgba(91,82,232,0.06);'>
        <div style='display:flex; align-items:center; gap:0.6rem;'>
            <span style='font-size:1.1rem;'>📊</span>
            <span style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1rem;
                font-weight:700; color:#3d3d5c;'>
                Tren Show Up (%) & Paid (%)
                {f"<span style='color:#9194b3; font-weight:500;'> — {title_prefix}</span>" if title_prefix else ""}
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

    df_copy = df.copy() if not use_loader else pd.DataFrame()
    if not use_loader:
        df_copy["tanggal"] = pd.to_datetime(df_copy["tanggal"])

    # Key unik berdasarkan prefix + mode centers
    centers_str = str(centers) if centers else "all"
    safe_key = (title_prefix + "_" + centers_str).replace(" ", "_").replace("-", "_").replace("[", "").replace("]", "").replace(",", "").replace("'", "").replace('"', "")[:60]

    view = st.radio(
        "Tampilan",
        ["Week on Week", "Month on Month"],
        horizontal=True,
        key=f"trend_view_{safe_key}",
        label_visibility="collapsed",
    )

    if view == "Week on Week":
        if use_loader:
            data_wow = trend_data.get("wow", pd.DataFrame())
        else:
            data_wow = build_wow_data(df_copy)

        if data_wow is None or data_wow.empty:
            st.info("Belum cukup data untuk chart Week on Week.")
            return

        total_weeks = len(data_wow)
        col_f1, col_f2, _ = st.columns([1, 1, 3])
        with col_f1:
            min_w = st.number_input("Dari minggu ke-", min_value=1,
                                    max_value=total_weeks, value=max(1, total_weeks-7),
                                    key=f"wow_from_{safe_key}")
        with col_f2:
            max_w = st.number_input("Sampai minggu ke-", min_value=1,
                                    max_value=total_weeks, value=total_weeks,
                                    key=f"wow_to_{safe_key}")

        data_filtered = data_wow.iloc[int(min_w)-1 : int(max_w)].reset_index(drop=True)
        labels      = data_filtered["label"].tolist()
        showup_vals = data_filtered["showup_pct"].tolist()
        paid_vals   = data_filtered["paid_pct"].tolist()
        period_label = "Minggu"

    else:
        if use_loader:
            data_mom = trend_data.get("mom", pd.DataFrame())
        else:
            data_mom = build_mom_data(df_copy)

        if data_mom is None or data_mom.empty:
            st.info("Belum cukup data untuk chart Month on Month.")
            return

        available_months = data_mom["label"].tolist()
        col_f1, col_f2, _ = st.columns([1, 1, 2])
        with col_f1:
            from_month = st.selectbox("Dari bulan", available_months,
                                      index=0,
                                      key=f"mom_from_{safe_key}")
        with col_f2:
            to_month = st.selectbox("Sampai bulan", available_months,
                                    index=len(available_months)-1,
                                    key=f"mom_to_{safe_key}")

        from_idx = available_months.index(from_month)
        to_idx   = available_months.index(to_month)
        if from_idx > to_idx:
            from_idx, to_idx = to_idx, from_idx

        data_filtered = data_mom.iloc[from_idx : to_idx+1].reset_index(drop=True)
        labels      = data_filtered["label"].tolist()
        showup_vals = data_filtered["showup_pct"].tolist()
        paid_vals   = data_filtered["paid_pct"].tolist()
        period_label = "Bulan"

    col1, col2 = st.columns(2)
    with col1:
        fig1 = make_bar_chart(
            labels, showup_vals,
            f"Show Up (%) per {period_label}",
            "rgba(91,82,232,0.7)"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = make_bar_chart(
            labels, paid_vals,
            f"Paid (%) per {period_label}",
            "rgba(5,150,105,0.7)"
        )
        st.plotly_chart(fig2, use_container_width=True)

    view = st.radio(
        "Tampilan",
        ["Week on Week", "Month on Month"],
        horizontal=True,
        key=f"trend_view_{title_prefix.replace(" ", "_")}",
        label_visibility="collapsed",
    )

    bulan_names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]

    if view == "Week on Week":
        # ── Filter rentang minggu ─────────────────────────────────────────────
        data_wow = build_wow_data(df)
        if data_wow.empty:
            st.info("Belum cukup data untuk chart Week on Week.")
            return

        total_weeks = len(data_wow)
        col_f1, col_f2, _ = st.columns([1, 1, 3])
        with col_f1:
            min_w = st.number_input("Dari minggu ke-", min_value=1,
                                    max_value=total_weeks, value=max(1, total_weeks-7),
                                    key=f"wow_from_{title_prefix.replace(" ", "_")}")
        with col_f2:
            max_w = st.number_input("Sampai minggu ke-", min_value=1,
                                    max_value=total_weeks, value=total_weeks,
                                    key=f"wow_to_{title_prefix.replace(" ", "_")}")

        data_filtered = data_wow.iloc[int(min_w)-1 : int(max_w)].reset_index(drop=True)
        labels      = data_filtered["label"].tolist()
        showup_vals = data_filtered["showup_pct"].tolist()
        paid_vals   = data_filtered["paid_pct"].tolist()
        period_label = "Minggu"

    else:
        # ── Filter rentang bulan ──────────────────────────────────────────────
        data_mom = build_mom_data(df)
        if data_mom.empty:
            st.info("Belum cukup data untuk chart Month on Month.")
            return

        available_months = data_mom["label"].tolist()
        col_f1, col_f2, _ = st.columns([1, 1, 2])
        with col_f1:
            from_month = st.selectbox("Dari bulan", available_months,
                                      index=0,
                                      key=f"mom_from_{title_prefix.replace(" ", "_")}")
        with col_f2:
            to_month = st.selectbox("Sampai bulan", available_months,
                                    index=len(available_months)-1,
                                    key=f"mom_to_{title_prefix.replace(" ", "_")}")

        from_idx = available_months.index(from_month)
        to_idx   = available_months.index(to_month)
        if from_idx > to_idx:
            from_idx, to_idx = to_idx, from_idx

        data_filtered = data_mom.iloc[from_idx : to_idx+1].reset_index(drop=True)
        labels      = data_filtered["label"].tolist()
        showup_vals = data_filtered["showup_pct"].tolist()
        paid_vals   = data_filtered["paid_pct"].tolist()
        period_label = "Bulan"

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
