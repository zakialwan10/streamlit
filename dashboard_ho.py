import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from auth import get_all_performance, get_sheet_df, ACTIVE_CENTERS
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

def show_ho_dashboard():
    nama = st.session_state.nama
    now  = datetime.now()
    bulan_names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]

    st.markdown(f"""
    <h2 style='font-family:'Plus Jakarta Sans',sans-serif; font-size:1.35rem; font-weight:800; letter-spacing:-0.01em;
        color:#1e1e2e; margin-bottom:0.3rem;'>HO Dashboard — {nama}</h2>
    <p style='color:#6b6f8e; margin-bottom:1.5rem; font-size:0.9rem;'>
        Overview performa seluruh center & EC
    </p>""", unsafe_allow_html=True)

    # ── Load semua data ───────────────────────────────────────────────────────
    df_all = get_all_performance()
    if df_all.empty:
        st.warning("Belum ada data performa.")
        return

    # ── Filter Bar ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])

    with col1:
        center_opts = ["Semua Center"] + ACTIVE_CENTERS
        selected_center = st.selectbox("📍 Center", center_opts)

    # EC dropdown berdasarkan center
    if selected_center == "Semua Center":
        ec_opts_df = df_all
    else:
        ec_opts_df = df_all[df_all["center"] == selected_center]

    ec_list = ["Semua EC"] + sorted(ec_opts_df["nama_ec"].unique().tolist())
    with col2:
        selected_ec = st.selectbox("👤 EC", ec_list)

    with col3:
        tahun = st.selectbox("📅 Tahun", [2025, 2026, 2027], index=1)
    with col4:
        bulan = st.selectbox("🗓 Bulan", list(range(1,13)),
                             format_func=lambda x: bulan_names[x-1],
                             index=now.month - 1)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filter data ───────────────────────────────────────────────────────────
    df = df_all.copy()
    df = df[(df["tanggal"].dt.year == tahun) & (df["tanggal"].dt.month == bulan)]
    if selected_center != "Semua Center":
        df = df[df["center"] == selected_center]
    if selected_ec != "Semua EC":
        df = df[df["nama_ec"] == selected_ec]

    # ── Global KPI ────────────────────────────────────────────────────────────
    total_b  = df["booking"].sum()
    total_su = df["show_up"].sum()
    total_p  = df["paid"].sum()
    avg_su   = safe_pct(total_su, total_b)
    avg_pd   = safe_pct(total_p, total_su)

    c1,c2,c3,c4,c5 = st.columns(5)
    kpis = [
        ("📋 Total Booking", str(total_b),  "#5b52e8", "rgba(91,82,232,0.08)",  "rgba(91,82,232,0.25)"),
        ("👣 Total Show Up", str(total_su), "#2563eb", "rgba(37,99,235,0.08)",  "rgba(37,99,235,0.25)"),
        ("💰 Total Paid",    str(total_p),  "#7c3aed", "rgba(124,58,237,0.08)", "rgba(124,58,237,0.25)"),
        ("📊 Show Up %",     f"{avg_su}%",  "#d97706", "rgba(217,119,6,0.08)",  "rgba(217,119,6,0.25)"),
        ("✅ Paid %",        f"{avg_pd}%",  "#059669", "rgba(5,150,105,0.08)",  "rgba(5,150,105,0.25)"),
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

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 Per Center", "🏆 Leaderboard EC", "📈 Tren Bulanan", "🎯 Performance Score"])

    with tab1:
        st.markdown("#### Performa per Center")
        center_rows = []
        for c in ACTIVE_CENTERS:
            dc = df_all[
                (df_all["center"] == c) &
                (df_all["tanggal"].dt.year == tahun) &
                (df_all["tanggal"].dt.month == bulan)
            ]
            b  = dc["booking"].sum()
            su = dc["show_up"].sum()
            p  = dc["paid"].sum()
            center_rows.append({
                "Center": c,
                "Booking": b, "Show Up": su, "Paid": p,
                "Show Up %": safe_pct(su, b),
                "Paid %": safe_pct(p, su),
                "Jumlah EC": dc["nama_ec"].nunique()
            })
        df_c = pd.DataFrame(center_rows).sort_values("Show Up %", ascending=False)

        rows_html = ""
        for _, row in df_c.iterrows():
            su_c = "#059669" if row["Show Up %"] >= 75 else "#d97706" if row["Show Up %"] >= 50 else "#dc2626"
            pd_c = "#059669" if row["Paid %"]    >= 75 else "#d97706" if row["Paid %"]    >= 50 else "#dc2626"
            rows_html += f"""
            <tr style='border-bottom:1px solid #eef0f8;'>
                <td style='padding:0.8rem 1rem; font-weight:700; color:#1e1e2e;'>{row['Center']}</td>
                <td style='padding:0.8rem 1rem; text-align:center; color:#3d3d5c;'>{row['Jumlah EC']}</td>
                <td style='padding:0.8rem 1rem; text-align:center; color:#3d3d5c;'>{int(row['Booking'])}</td>
                <td style='padding:0.8rem 1rem; text-align:center; color:#3d3d5c;'>{int(row['Show Up'])}</td>
                <td style='padding:0.8rem 1rem; text-align:center;'>
                    <span style='background:{su_c}18; color:{su_c}; border-radius:99px;
                        padding:0.2rem 0.7rem; font-weight:700;'>{row['Show Up %']}%</span>
                </td>
                <td style='padding:0.8rem 1rem; text-align:center; color:#3d3d5c;'>{int(row['Paid'])}</td>
                <td style='padding:0.8rem 1rem; text-align:center;'>
                    <span style='background:{pd_c}18; color:{pd_c}; border-radius:99px;
                        padding:0.2rem 0.7rem; font-weight:700;'>{row['Paid %']}%</span>
                </td>
            </tr>"""

        st.markdown(f"""
        <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
            <table style='width:100%; border-collapse:collapse;'>
                <thead><tr style='background:#f5f6fc;'>
                    <th style='padding:0.8rem 1rem; text-align:left; color:#6b6f8e; font-size:0.8rem;'>CENTER</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>JML EC</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>BOOKING</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>SHOW UP</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>SHOW UP %</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>PAID</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>PAID %</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("#### 🏆 Leaderboard EC")
        df_lb = df.groupby(["nama_ec","center"]).agg(
            booking=("booking","sum"), show_up=("show_up","sum"), paid=("paid","sum")
        ).reset_index()
        df_lb["showup_pct"] = df_lb.apply(lambda r: safe_pct(r["show_up"], r["booking"]), axis=1)
        df_lb["paid_pct"]   = df_lb.apply(lambda r: safe_pct(r["paid"], r["show_up"]), axis=1)
        df_lb = df_lb.sort_values("showup_pct", ascending=False).reset_index(drop=True)

        medals = ["🥇","🥈","🥉"]
        rows_html = ""
        for i, row in df_lb.iterrows():
            su_c = "#059669" if row["showup_pct"] >= 75 else "#d97706" if row["showup_pct"] >= 50 else "#dc2626"
            pd_c = "#059669" if row["paid_pct"]   >= 75 else "#d97706" if row["paid_pct"]   >= 50 else "#dc2626"
            rank = medals[i] if i < 3 else f"#{i+1}"
            rows_html += f"""
            <tr style='border-bottom:1px solid #eef0f8;'>
                <td style='padding:0.8rem 1rem; font-size:1rem; font-weight:700;'>{rank}</td>
                <td style='padding:0.8rem 1rem; color:#1e1e2e; font-weight:500;'>{row['nama_ec']}</td>
                <td style='padding:0.8rem 1rem; color:#6b6f8e;'>{row['center']}</td>
                <td style='padding:0.8rem 1rem; text-align:center; color:#3d3d5c;'>{int(row['booking'])}</td>
                <td style='padding:0.8rem 1rem; text-align:center;'>
                    <span style='background:{su_c}18; color:{su_c}; border-radius:99px;
                        padding:0.2rem 0.7rem; font-weight:700;'>{row['showup_pct']}%</span>
                </td>
                <td style='padding:0.8rem 1rem; text-align:center;'>
                    <span style='background:{pd_c}18; color:{pd_c}; border-radius:99px;
                        padding:0.2rem 0.7rem; font-weight:700;'>{row['paid_pct']}%</span>
                </td>
            </tr>"""

        st.markdown(f"""
        <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
            <table style='width:100%; border-collapse:collapse;'>
                <thead><tr style='background:#f5f6fc;'>
                    <th style='padding:0.8rem 1rem; text-align:left; color:#6b6f8e; font-size:0.8rem;'>#</th>
                    <th style='padding:0.8rem 1rem; text-align:left; color:#6b6f8e; font-size:0.8rem;'>NAMA EC</th>
                    <th style='padding:0.8rem 1rem; text-align:left; color:#6b6f8e; font-size:0.8rem;'>CENTER</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>BOOKING</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>SHOW UP %</th>
                    <th style='padding:0.8rem 1rem; text-align:center; color:#6b6f8e; font-size:0.8rem;'>PAID %</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)

    with tab4:
        st.markdown("#### 🎯 Performance Score Semua EC")
        from scoring import load_all_ec_scores
        df_sc = load_all_ec_scores()
        if df_sc.empty:
            st.info("Belum ada data score.")
        else:
            df_sc_f = df_sc[df_sc["bulan"] == bulan_names[bulan-1]].copy()
            if selected_center != "Semua Center":
                df_sc_f = df_sc_f[df_sc_f["location"].str.upper() == selected_center]
            if selected_ec != "Semua EC":
                df_sc_f = df_sc_f[df_sc_f["ec_name"] == selected_ec]
            df_sc_f = df_sc_f.sort_values("total_score", ascending=False).reset_index(drop=True)

            medals = ["🥇","🥈","🥉"]
            rows_html = ""
            for i, row in df_sc_f.iterrows():
                rank = medals[i] if i < 3 else f"#{i+1}"
                cat = row["category"]
                cat_color = row["category_color"]
                score = row["total_score"]
                bar_color = "#059669" if score >= 85 else "#d97706" if score >= 75 else "#dc2626"
                rows_html += f"""
                <tr style='border-bottom:1px solid #eef0f8;'>
                    <td style='padding:0.7rem 1rem; font-weight:700;'>{rank}</td>
                    <td style='padding:0.7rem 1rem; color:#1e1e2e; font-weight:500;'>{row['ec_name']}</td>
                    <td style='padding:0.7rem 1rem; color:#6b6f8e;'>{row['location']}</td>
                    <td style='padding:0.7rem 1rem;'>
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
                    <td style='padding:0.7rem 0.8rem; text-align:center; color:#6b6f8e; font-size:0.82rem;'>
                        {row.get('paid_cvr',0)*100:.0f}% / {row.get('fp_sameday',0)*100:.0f}% / {row.get('m0',0)*100:.0f}%
                    </td>
                </tr>"""

            st.markdown(f"""
            <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px; overflow:hidden;'>
                <table style='width:100%; border-collapse:collapse;'>
                    <thead><tr style='background:#f5f6fc;'>
                        <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>#</th>
                        <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>NAMA EC</th>
                        <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>CENTER</th>
                        <th style='padding:0.7rem 1rem; text-align:left; color:#6b6f8e; font-size:0.78rem;'>SCORE</th>
                        <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>CATEGORY</th>
                        <th style='padding:0.7rem 1rem; text-align:center; color:#6b6f8e; font-size:0.78rem;'>CVR / FP / M0</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.markdown("#### 📈 Tren Show Up % & Paid %")
        df_trend = df_all.copy()
        if selected_center != "Semua Center":
            df_trend = df_trend[df_trend["center"] == selected_center]
        if selected_ec != "Semua EC":
            df_trend = df_trend[df_trend["nama_ec"] == selected_ec]

        from charts_trend import show_trend_charts
        from auth import ACTIVE_CENTERS
        if selected_ec != "Semua EC":
            # Per EC — gunakan data harian
            show_trend_charts(df_trend, f"HO_{selected_ec}", centers="ec")
        elif selected_center != "Semua Center":
            # Per Center — gunakan wow_mom_data
            show_trend_charts(df_trend, f"HO_{selected_center}", centers=[selected_center])
        else:
            # Semua Center — gunakan wow_mom_data
            show_trend_charts(df_trend, "HO_Semua_Center", centers=ACTIVE_CENTERS)
