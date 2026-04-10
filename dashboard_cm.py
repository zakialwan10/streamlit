import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from auth import get_performance_df, get_sheet_df
from datetime import datetime

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#1e1e2e", family="DM Sans"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="rgba(0,0,0,0.06)", showline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)", showline=False),
)

def safe_pct(num, den):
    return round((num / den * 100), 1) if den > 0 else 0.0

def show_cm_dashboard():
    nama      = st.session_state.nama
    center_id = st.session_state.center_id
    now       = datetime.now()
    bulan_names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]

    st.markdown(f"""
    <h2 style='font-family:'Plus Jakarta Sans',sans-serif; font-size:1.35rem; font-weight:800; letter-spacing:-0.01em;
        color:#1e1e2e; margin-bottom:0.3rem;'>Dashboard CM — {nama}</h2>
    <p style='color:#6b6f8e; margin-bottom:1.5rem; font-size:0.9rem;'>
        Performa seluruh EC di Center <b>{center_id}</b>
    </p>""", unsafe_allow_html=True)

    # ── Filter ────────────────────────────────────────────────────────────────
    col_y, col_m, col_s, _ = st.columns([1, 1, 1.5, 2])
    with col_y:
        tahun = st.selectbox("Tahun", [2025, 2026, 2027], index=1)
    with col_m:
        bulan = st.selectbox("Bulan", list(range(1,13)),
                             format_func=lambda x: bulan_names[x-1],
                             index=now.month - 1)
    sort_options = {
        "Show Up % Tertinggi": ("showup_pct", False),
        "Show Up % Terendah":  ("showup_pct", True),
        "Paid % Tertinggi":    ("paid_pct",   False),
        "Paid % Terendah":     ("paid_pct",   True),
        "Booking Tertinggi":   ("booking",    False),
        "Nama A-Z":            ("nama_ec",    True),
    }
    with col_s:
        sort_label = st.selectbox("Urutkan", list(sort_options.keys()))

    # ── Ambil & filter data ───────────────────────────────────────────────────
    df = get_performance_df(center_id)
    if df.empty:
        st.warning(f"Belum ada data untuk performance_{center_id}.")
        return

    df_period = df[
        (df["tanggal"].dt.year == tahun) &
        (df["tanggal"].dt.month == bulan)
    ]

    # Agregat per EC
    summary = df_period.groupby("nama_ec").agg(
        booking=("booking", "sum"),
        show_up=("show_up", "sum"),
        paid=("paid", "sum")
    ).reset_index()
    summary["showup_pct"] = summary.apply(lambda r: safe_pct(r["show_up"], r["booking"]), axis=1)
    summary["paid_pct"]   = summary.apply(lambda r: safe_pct(r["paid"], r["show_up"]), axis=1)

    sort_col, sort_asc = sort_options[sort_label]
    summary = summary.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

    # ── KPI Center ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    total_b  = summary["booking"].sum()
    total_su = summary["show_up"].sum()
    total_p  = summary["paid"].sum()
    avg_su   = safe_pct(total_su, total_b)
    avg_pd   = safe_pct(total_p, total_su)

    c1,c2,c3,c4,c5 = st.columns(5)
    kpis = [
        ("👥 Jumlah EC",     str(len(summary)), "#5b52e8", "rgba(91,82,232,0.08)",  "rgba(91,82,232,0.25)"),
        ("📋 Total Booking", str(total_b),      "#2563eb", "rgba(37,99,235,0.08)",  "rgba(37,99,235,0.25)"),
        ("👣 Total Show Up", str(total_su),     "#7c3aed", "rgba(124,58,237,0.08)", "rgba(124,58,237,0.25)"),
        ("📊 Avg Show Up %", f"{avg_su}%",      "#d97706", "rgba(217,119,6,0.08)",  "rgba(217,119,6,0.25)"),
        ("✅ Avg Paid %",    f"{avg_pd}%",      "#059669", "rgba(5,150,105,0.08)",  "rgba(5,150,105,0.25)"),
    ]
    for col, (label, val, color, bg, border) in zip([c1,c2,c3,c4,c5], kpis):
        with col:
            st.markdown(f"""
            <div style='background:{bg}; border:1px solid {border};
                border-radius:16px; padding:1rem; text-align:center;'>
                <div style='color:#6b6f8e; font-size:0.92rem; font-weight:600; margin-bottom:0.5rem;'>{label}</div>
                <div style='font-family:'Plus Jakarta Sans',sans-serif; font-size:1.2rem;
                    font-weight:700; color:{color};'>{val}</div>
            </div>""", unsafe_allow_html=True)

    # ── Tabel EC ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""<h3 style='font-family:'Plus Jakarta Sans',sans-serif; font-size:0.95rem; font-weight:700;
        color:#3d3d5c; margin-bottom:1rem;'>📋 Detail Performa EC</h3>""", unsafe_allow_html=True)

    rows_html = ""
    for i, row in summary.iterrows():
        su  = row["showup_pct"]
        pd_ = row["paid_pct"]
        su_color  = "#059669" if su  >= 75 else "#d97706" if su  >= 50 else "#dc2626"
        pd_color  = "#059669" if pd_ >= 75 else "#d97706" if pd_ >= 50 else "#dc2626"

        rows_html += f"""
        <tr style='border-bottom:1px solid #eef0f8;'>
            <td style='padding:0.8rem 1rem; color:#1e1e2e; font-weight:600;'>{row['nama_ec']}</td>
            <td style='padding:0.8rem 1rem; color:#3d3d5c; text-align:center;'>{int(row['booking'])}</td>
            <td style='padding:0.8rem 1rem; color:#3d3d5c; text-align:center;'>{int(row['show_up'])}</td>
            <td style='padding:0.8rem 1rem; text-align:center;'>
                <span style='background:{su_color}18; color:{su_color}; border-radius:99px;
                    padding:0.2rem 0.7rem; font-weight:700; font-size:0.9rem;'>{su}%</span>
            </td>
            <td style='padding:0.8rem 1rem; color:#3d3d5c; text-align:center;'>{int(row['paid'])}</td>
            <td style='padding:0.8rem 1rem; text-align:center;'>
                <span style='background:{pd_color}18; color:{pd_color}; border-radius:99px;
                    padding:0.2rem 0.7rem; font-weight:700; font-size:0.9rem;'>{pd_}%</span>
            </td>
        </tr>"""

    st.markdown(f"""
    <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
        <table style='width:100%; border-collapse:collapse;'>
            <thead>
                <tr style='background:#f5f6fc;'>
                    <th style='padding:0.8rem 1rem; text-align:left; color:#6b6f8e; font-size:0.8rem;'>NAMA EC</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>BOOKING</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>SHOW UP</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>SHOW UP %</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>PAID</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>PAID %</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)

    # ── Performance Score ─────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    show_cm_score_table(center_id, bulan_names[bulan-1])

    # ── Bar Chart ─────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 Show Up % per EC", "✅ Paid % per EC"])

    with tab1:
        fig = go.Figure(go.Bar(
            x=summary["nama_ec"], y=summary["showup_pct"],
            marker_color=["#059669" if v >= 75 else "#d97706" if v >= 50 else "#dc2626"
                          for v in summary["showup_pct"]],
            text=[f"{v}%" for v in summary["showup_pct"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Show Up %: %{y}%<extra></extra>"
        ))
        fig.update_layout(**PLOTLY_LAYOUT, yaxis_range=[0, 110])
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure(go.Bar(
            x=summary["nama_ec"], y=summary["paid_pct"],
            marker_color=["#059669" if v >= 75 else "#d97706" if v >= 50 else "#dc2626"
                          for v in summary["paid_pct"]],
            text=[f"{v}%" for v in summary["paid_pct"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Paid %: %{y}%<extra></extra>"
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, yaxis_range=[0, 110])
        st.plotly_chart(fig2, use_container_width=True)

    # ── WoW / MoM Trend Charts ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    from charts_trend import show_trend_charts
    show_trend_charts(df, f"Center {center_id}")


def show_cm_score_table(center_id: str, bulan_label: str):
    """Tampilkan tabel score semua EC di center CM."""
    from scoring import load_all_ec_scores, get_category

    st.markdown("""<h3 style='font-family:"Plus Jakarta Sans",sans-serif; font-size:0.95rem;
        font-weight:700; color:#3d3d5c; margin-bottom:1rem;'>
        🏆 Performance Score EC</h3>""", unsafe_allow_html=True)

    df_scores = load_all_ec_scores()
    if df_scores.empty:
        st.info("Belum ada data score.")
        return

    df = df_scores[
        (df_scores["location"].str.strip().str.upper() == center_id.strip().upper()) &
        (df_scores["bulan"] == bulan_label)
    ].copy()

    if df.empty:
        st.info(f"Belum ada data score untuk Center {center_id} bulan {bulan_label}.")
        return

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)

    medals = ["🥇","🥈","🥉"]
    rows_html = ""
    for i, row in df.iterrows():
        rank = medals[i] if i < 3 else f"#{i+1}"
        cat = row["category"]
        cat_color = row["category_color"]
        score = row["total_score"]
        bar_color = "#059669" if score >= 85 else "#d97706" if score >= 75 else "#dc2626"

        rows_html += f"""
        <tr style='border-bottom:1px solid #eef0f8;'>
            <td style='padding:0.7rem 1rem; font-weight:700;'>{rank}</td>
            <td style='padding:0.7rem 1rem; color:#1e1e2e; font-weight:500;'>{row['ec_name']}</td>
            <td style='padding:0.7rem 1rem; text-align:center;'>
                <div style='display:flex; align-items:center; gap:0.5rem;'>
                    <div style='flex:1; background:rgba(0,0,0,0.08); border-radius:99px; height:8px; overflow:hidden;'>
                        <div style='height:100%; width:{min(score,100):.1f}%; background:{bar_color}; border-radius:99px;'></div>
                    </div>
                    <span style='font-family:"Plus Jakarta Sans",sans-serif; color:{bar_color};
                        font-weight:800; font-size:1rem; min-width:35px;'>{score:.0f}</span>
                </div>
            </td>
            <td style='padding:0.7rem 1rem; text-align:center;'>
                <span style='background:{cat_color}18; color:{cat_color}; border-radius:99px;
                    padding:0.2rem 0.8rem; font-size:0.78rem; font-weight:600;'>{cat if cat else '-'}</span>
            </td>
            <td style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.85rem;'>
                {row.get('paid_cvr',0)*100:.0f}% / {row.get('fp_sameday',0)*100:.0f}% / {row.get('m0',0)*100:.0f}%
            </td>
        </tr>"""

    st.markdown(f"""
    <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
        <table style='width:100%; border-collapse:collapse;'>
            <thead><tr style='background:#f5f6fc;'>
                <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>#</th>
                <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>NAMA EC</th>
                <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>SCORE</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>CATEGORY</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>CVR / FP / M0</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
