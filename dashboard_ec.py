import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from auth import get_performance_df, get_sheet_df
from datetime import datetime

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#1e1e2e", family="DM Sans"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="rgba(0,0,0,0.06)", showline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)", showline=False),
)

def safe_pct(num, den):
    return round((num / den * 100), 1) if den > 0 else 0.0

def show_ec_dashboard():
    username  = st.session_state.username
    nama      = st.session_state.nama
    center_id = st.session_state.center_id
    now       = datetime.now()

    st.markdown(f"""
    <h2 style='font-family:'Plus Jakarta Sans',sans-serif; font-size:1.35rem; font-weight:800; letter-spacing:-0.01em;
        color:#1e1e2e; margin-bottom:0.3rem;'>Halo, {nama} 👋</h2>
    <p style='color:#6b6f8e; margin-bottom:1.5rem; font-size:0.9rem;'>
        Pantau performa Anda di Center <b>{center_id}</b>
    </p>""", unsafe_allow_html=True)

    # ── Periode ──────────────────────────────────────────────────────────────
    bulan_names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
    col_y, col_m, _ = st.columns([1, 1, 3])
    with col_y:
        tahun = st.selectbox("Tahun", [2025, 2026, 2027], index=1)
    with col_m:
        bulan = st.selectbox("Bulan", list(range(1,13)),
                             format_func=lambda x: bulan_names[x-1],
                             index=now.month - 1)

    # ── Ambil data EC ini saja ────────────────────────────────────────────────
    df_center = get_performance_df(center_id)
    if df_center.empty:
        st.warning("Belum ada data performa untuk center Anda.")
        return

    df_ec = df_center[df_center["nama_ec"].str.strip().str.lower() == nama.strip().lower()]
    if df_ec.empty:
        st.warning(f"Tidak ditemukan data untuk nama '{nama}' di sheet performance_{center_id}.")
        st.info("Pastikan nama di sheet Google Sheets sama persis dengan nama_lengkap di sheet users.")
        return

    df_period = df_ec[
        (df_ec["tanggal"].dt.year == tahun) &
        (df_ec["tanggal"].dt.month == bulan)
    ]

    # ── Hitung metrik ─────────────────────────────────────────────────────────
    total_booking = df_period["booking"].sum()
    total_showup  = df_period["show_up"].sum()
    total_paid    = df_period["paid"].sum()
    showup_pct    = safe_pct(total_showup, total_booking)
    paid_pct      = safe_pct(total_paid, total_showup)

    # ── KPI Cards ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        ("📋 Total Booking", str(total_booking), "#5b52e8", "rgba(91,82,232,0.08)", "rgba(91,82,232,0.25)"),
        ("👣 Total Show Up",  str(total_showup),  "#2563eb", "rgba(37,99,235,0.08)",  "rgba(37,99,235,0.25)"),
        ("💰 Show Up %",     f"{showup_pct}%",   "#7c3aed", "rgba(124,58,237,0.08)", "rgba(124,58,237,0.25)"),
        ("✅ Paid %",        f"{paid_pct}%",     "#059669", "rgba(5,150,105,0.08)",  "rgba(5,150,105,0.25)"),
    ]
    for col, (label, val, color, bg, border) in zip([c1,c2,c3,c4], kpis):
        with col:
            st.markdown(f"""
            <div style='background:{bg}; border:1px solid {border};
                border-radius:16px; padding:1.2rem; text-align:center;'>
                <div style='color:#6b6f8e; font-size:0.92rem; font-weight:600; margin-bottom:0.5rem;'>{label}</div>
                <div style='font-family:'Plus Jakarta Sans',sans-serif; font-size:1.25rem;
                    font-weight:700; color:{color};'>{val}</div>
            </div>""", unsafe_allow_html=True)

    # ── Gauge Charts ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)

    def make_gauge(title, value, color):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 32, "color": color}},
            title={"text": title, "font": {"size": 14, "color": "#1e1e2e"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#6b6f8e"},
                "bar": {"color": color},
                "bgcolor": "rgba(0,0,0,0.05)",
                "steps": [
                    {"range": [0, 50],  "color": "rgba(239,68,68,0.1)"},
                    {"range": [50, 75], "color": "rgba(250,204,21,0.1)"},
                    {"range": [75, 100],"color": "rgba(5,150,105,0.1)"},
                ],
                "threshold": {"line": {"color": color, "width": 3}, "value": value}
            }
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=220,
                          margin=dict(l=20, r=20, t=40, b=10),
                          font=dict(family="DM Sans"))
        return fig

    with g1:
        st.plotly_chart(make_gauge("Show Up %", showup_pct, "#5b52e8"), use_container_width=True)
    with g2:
        st.plotly_chart(make_gauge("Paid %", paid_pct, "#059669"), use_container_width=True)

    # ── WoW / MoM Trend Charts ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    from charts_trend import show_trend_charts
    show_trend_charts(df_ec, f"EC_{nama}", centers="ec")

    # ── Performance Score ─────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    show_ec_score_section(nama, bulan_names[bulan-1])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""<h3 style='font-family:"Plus Jakarta Sans",sans-serif; font-size:0.95rem;
        font-weight:700; color:#3d3d5c; margin-bottom:1rem;'>📅 Tren Harian</h3>""",
        unsafe_allow_html=True)

    if not df_period.empty:
        df_daily = df_period.groupby("tanggal")[["booking","show_up","paid"]].sum().reset_index()
        df_daily["showup_pct"] = df_daily.apply(lambda r: safe_pct(r["show_up"], r["booking"]), axis=1)
        df_daily["paid_pct"]   = df_daily.apply(lambda r: safe_pct(r["paid"], r["show_up"]), axis=1)

        tab1, tab2 = st.tabs(["📊 Volume (Booking/Show Up/Paid)", "📈 Persentase (%)"])
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_daily["tanggal"], y=df_daily["booking"],
                name="Booking", marker_color="rgba(91,82,232,0.7)"))
            fig.add_trace(go.Bar(x=df_daily["tanggal"], y=df_daily["show_up"],
                name="Show Up", marker_color="rgba(37,99,235,0.7)"))
            fig.add_trace(go.Bar(x=df_daily["tanggal"], y=df_daily["paid"],
                name="Paid", marker_color="rgba(5,150,105,0.7)"))
            fig.update_layout(**PLOTLY_LAYOUT, barmode="group",
                legend=dict(orientation="h", y=1.1, font=dict(color="#1e1e2e")))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_daily["tanggal"], y=df_daily["showup_pct"],
                name="Show Up %", mode="lines+markers",
                line=dict(color="#5b52e8", width=2.5), marker=dict(size=6)))
            fig2.add_trace(go.Scatter(x=df_daily["tanggal"], y=df_daily["paid_pct"],
                name="Paid %", mode="lines+markers",
                line=dict(color="#059669", width=2.5), marker=dict(size=6)))
            fig2.update_layout(**PLOTLY_LAYOUT,
                legend=dict(orientation="h", y=1.1, font=dict(color="#1e1e2e")))
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Belum ada data untuk periode ini.")


def show_ec_score_section(nama: str, bulan_label: str):
    """Tampilkan section score EC."""
    from scoring import load_all_ec_scores, get_ec_score, TARGETS, WEIGHTS

    df_scores = load_all_ec_scores()
    score_data = get_ec_score(nama, bulan_label, df_scores)

    st.markdown("""<h3 style='font-family:"Plus Jakarta Sans",sans-serif; font-size:0.95rem;
        font-weight:700; color:#3d3d5c; margin-bottom:1rem;'>
        🏆 Performance Score</h3>""", unsafe_allow_html=True)

    if score_data is None or score_data.get("total_score", 0) == 0:
        st.info(f"Belum ada data score untuk bulan {bulan_label}.")
        return

    total = score_data["total_score"]
    cat = score_data["category"]
    cat_color = score_data["category_color"]
    detail = score_data["score_detail"]

    # Total score card
    cat_bg = {"#059669": "rgba(5,150,105,0.08)", "#d97706": "rgba(217,119,6,0.08)", "#dc2626": "rgba(220,38,38,0.08)"}.get(cat_color, "rgba(107,111,142,0.08)")
    cat_border = {"#059669": "rgba(5,150,105,0.3)", "#d97706": "rgba(217,119,6,0.3)", "#dc2626": "rgba(220,38,38,0.3)"}.get(cat_color, "rgba(107,111,142,0.3)")

    st.markdown(f"""
    <div style='background:{cat_bg}; border:1.5px solid {cat_border};
        border-radius:16px; padding:1.5rem; text-align:center; margin-bottom:1.5rem;'>
        <div style='color:#6b6f8e; font-size:0.85rem; font-weight:600; margin-bottom:0.3rem;'>
            Total Performance Score
        </div>
        <div style='font-family:"Plus Jakarta Sans",sans-serif; font-size:2.5rem;
            font-weight:800; color:{cat_color}; line-height:1;'>{total}</div>
        <div style='margin-top:0.5rem;'>
            <span style='background:{cat_color}18; color:{cat_color}; border-radius:99px;
                padding:0.3rem 1rem; font-size:0.85rem; font-weight:600;'>{cat}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detail per metric
    metric_labels = {
        "paid_cvr":   ("Paid CVR",          f"{int(TARGETS['paid_cvr']*100)}%",   35),
        "fp_sameday": ("FP Sameday",         f"{int(TARGETS['fp_sameday']*100)}%", 20),
        "m0":         ("M0 %",               f"{int(TARGETS['m0']*100)}%",         10),
        "m1":         ("M1 %",               f"{int(TARGETS['m1']*100)}%",          5),
        "m2":         ("M2 %",               f"{int(TARGETS['m2']*100)}%",          5),
        "diversified":("Diversified Channel","100",                                25),
    }

    rows_html = ""
    for key, (label, target_str, weight_pct) in metric_labels.items():
        if key not in detail or not isinstance(detail[key], dict):
            continue
        d = detail[key]
        ach = d["achievement"]
        sc  = d["score"]
        fin = d["final"]
        if key == "diversified":
            ach_str = f"{ach:.1f}"
        else:
            ach_str = f"{ach*100:.1f}%"
        bar_color = "#059669" if sc >= 85 else "#d97706" if sc >= 70 else "#dc2626"
        bar_pct = min(sc, 100)  # cap visual bar di 100%, tapi angka tetap asli

        rows_html += f"""
        <tr style='border-bottom:1px solid #eef0f8;'>
            <td style='padding:0.7rem 1rem; color:#1e1e2e; font-weight:500;'>{label}</td>
            <td style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e;'>{target_str}</td>
            <td style='padding:0.7rem 1rem; text-align:center; color:#3d3d5c; font-weight:600;'>{ach_str}</td>
            <td style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e;'>{weight_pct}%</td>
            <td style='padding:0.7rem 1rem; min-width:130px;'>
                <div style='display:flex; align-items:center; gap:0.5rem;'>
                    <div style='flex:1; background:rgba(0,0,0,0.08); border-radius:99px; height:7px; overflow:hidden;'>
                        <div style='height:100%; width:{bar_pct:.1f}%; background:{bar_color}; border-radius:99px;'></div>
                    </div>
                    <span style='color:{bar_color}; font-weight:700; font-size:0.82rem; min-width:35px;'>{sc:.0f}</span>
                </div>
            </td>
            <td style='padding:0.7rem 1rem; text-align:center; color:{bar_color}; font-weight:700;'>{fin:.1f}</td>
        </tr>"""

    st.markdown(f"""
    <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
        <table style='width:100%; border-collapse:collapse;'>
            <thead><tr style='background:#f5f6fc;'>
                <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>METRIC</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>TARGET</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>ACHIEVEMENT</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>WEIGHT</th>
                <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>SCORE</th>
                <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>FINAL</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
