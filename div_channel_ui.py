"""
div_channel_ui.py — UI untuk menampilkan detail Diversified Channel Score per EC
"""
import streamlit as st
from datetime import datetime
from div_channel import calc_div_channel

BULAN_NAMES = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
BULAN_FULL  = ["Januari","Februari","Maret","April","Mei","Juni",
               "Juli","Agustus","September","Oktober","November","Desember"]


def _pct(val: float) -> str:
    return f"{val*100:.1f}%"

def _num(val) -> str:
    return str(int(val)) if isinstance(val, float) and val == int(val) else str(val)

def _score_color(score: float) -> str:
    if score >= 85: return "#059669"
    if score >= 70: return "#d97706"
    return "#dc2626"

def _row(label, value, value_color="#1e1e2e", bold=False):
    fw = "700" if bold else "400"
    return f"""
    <tr style='border-bottom:1px solid #f0f2f8;'>
        <td style='padding:0.6rem 1rem; color:#6b6f8e; font-size:0.88rem;'>{label}</td>
        <td style='padding:0.6rem 1rem; color:{value_color}; font-size:0.88rem;
            font-weight:{fw}; text-align:right;'>{value}</td>
    </tr>"""

def _section_header(title: str, score: float, weight_pct: str) -> str:
    sc = _score_color(score)
    return f"""
    <div style='background:#f8f9ff; border-left:4px solid #5b52e8;
        border-radius:0 8px 8px 0; padding:0.7rem 1rem; margin:1rem 0 0.5rem;
        display:flex; justify-content:space-between; align-items:center;'>
        <span style='font-family:"Plus Jakarta Sans",sans-serif; font-weight:700;
            font-size:0.9rem; color:#3d3d5c;'>{title}</span>
        <div style='display:flex; gap:0.5rem; align-items:center;'>
            <span style='color:#9194b3; font-size:0.78rem;'>bobot {weight_pct}</span>
            <span style='background:{sc}18; color:{sc}; border-radius:99px;
                padding:0.15rem 0.6rem; font-weight:700; font-size:0.85rem;'>
                {score:.1f}
            </span>
        </div>
    </div>"""

def _table_wrap(rows_html: str) -> str:
    return f"""
    <div style='background:#fff; border:1px solid #eef0f8; border-radius:12px;
        overflow:hidden; margin-bottom:0.5rem;'>
        <table style='width:100%; border-collapse:collapse;'>
            <tbody>{rows_html}</tbody>
        </table>
    </div>"""


def show_div_channel_detail(ec_name: str, center: str):
    """Tampilkan popup detail Diversified Channel Score untuk satu EC."""
    now = datetime.now()

    st.markdown(f"""
    <div style='background:#fff; border:1px solid #dde0f0; border-radius:16px;
        padding:1.5rem; margin-bottom:1rem;
        box-shadow:0 4px 20px rgba(91,82,232,0.08);'>
        <div style='display:flex; align-items:center; gap:0.8rem; margin-bottom:0.3rem;'>
            <span style='font-size:1.3rem;'>🎯</span>
            <span style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1.1rem;
                font-weight:800; color:#1e1e2e;'>Diversified Channel Score</span>
        </div>
        <p style='color:#9194b3; font-size:0.85rem; margin:0;'>
            {ec_name} &nbsp;·&nbsp; Center {center}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Pilih periode
    col_y, col_m, _ = st.columns([1, 1, 3])
    with col_y:
        year = st.selectbox("Tahun", [2025, 2026, 2027], index=1,
                            key=f"div_year_{ec_name}")
    with col_m:
        month = st.selectbox("Bulan", list(range(1, 13)),
                             format_func=lambda x: BULAN_NAMES[x-1],
                             index=now.month - 1,
                             key=f"div_month_{ec_name}")

    with st.spinner("Menghitung score..."):
        d = calc_div_channel(ec_name, center, year, month)

    # ── Total Score Card ──────────────────────────────────────────────────────
    div_color = _score_color(d["div_index"])
    st.markdown(f"""
    <div style='background:{div_color}10; border:2px solid {div_color}40;
        border-radius:16px; padding:1.5rem; text-align:center; margin:1rem 0;'>
        <div style='color:#6b6f8e; font-size:0.85rem; margin-bottom:0.3rem;'>
            Diversified Channel Index
        </div>
        <div style='font-family:"Plus Jakarta Sans",sans-serif; font-size:2.8rem;
            font-weight:800; color:{div_color}; line-height:1;'>
            {d["div_index"]:.1f}
        </div>
        <div style='color:#9194b3; font-size:0.8rem; margin-top:0.4rem;'>
            Total Score: {d["total_score"]:.1f} × 25%
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 1. Cross Sell Offline ─────────────────────────────────────────────────
    st.markdown(_section_header("1. Cross Sell Offline", d["cs_score"], "50%"),
                unsafe_allow_html=True)

    rows = ""
    rows += _row("#Shift", _num(d["cs_shift"]))
    rows += _row("#Leads", _num(d["cs_leads"]))
    rows += _row("#Booking OTS", _num(d["cs_booking_ots"]))
    rows += _row("#Booking FU", _num(d["cs_booking_fu"]))
    rows += _row("Total Booking", _num(d["cs_total_booking"]), bold=True)
    rows += _row("Booking/Shift",
                 f"{d['cs_booking_per_shift']:.2f}",
                 "#5b52e8", bold=True)
    rows += _row("Scoring",
                 f"{d['cs_score']:.2f}",
                 _score_color(d["cs_score"]), bold=True)
    st.markdown(_table_wrap(rows), unsafe_allow_html=True)

    # Formula hint
    st.markdown("""
    <p style='color:#b0b3c8; font-size:0.75rem; margin:0 0 1rem 0.5rem;'>
        Scoring = (Booking/Shift ÷ 1) × 100 × 50%
    </p>""", unsafe_allow_html=True)

    # ── 2. Referral Trial Day ─────────────────────────────────────────────────
    st.markdown(_section_header("2. Referral Trial Day", d["ref_score"], "20%"),
                unsafe_allow_html=True)

    rows = ""
    rows += _row("#Show Up", _num(d["ref_showup"]))
    rows += _row("#Referrer", _num(d["ref_referrer"]))
    rows += _row("%Referrer",
                 _pct(d["ref_pct"]),
                 "#5b52e8", bold=True)
    rows += _row("Scoring",
                 f"{d['ref_score']:.2f}",
                 _score_color(d["ref_score"]), bold=True)
    st.markdown(_table_wrap(rows), unsafe_allow_html=True)

    st.markdown("""
    <p style='color:#b0b3c8; font-size:0.75rem; margin:0 0 1rem 0.5rem;'>
        Scoring = (%Referrer ÷ 30%) × 100 × 20%
    </p>""", unsafe_allow_html=True)

    # ── 3. Offline Event ──────────────────────────────────────────────────────
    st.markdown(_section_header("3. Offline Event", d["ev_score"], "30%"),
                unsafe_allow_html=True)

    rows = ""
    rows += _row("#Shift", _num(d["ev_shift"]))
    rows += _row("#Leads", _num(d["ev_leads"]))
    rows += _row("#Booking OTS", _num(d["ev_booking_ots"]))
    rows += _row("#Booking FU", _num(d["ev_booking_fu"]))
    rows += _row("Total Booking", _num(d["ev_total_booking"]), bold=True)
    rows += _row("Booking/Shift",
                 f"{d['ev_booking_per_shift']:.2f}",
                 "#5b52e8", bold=True)
    rows += _row("Scoring",
                 f"{d['ev_score']:.2f}",
                 _score_color(d["ev_score"]), bold=True)
    st.markdown(_table_wrap(rows), unsafe_allow_html=True)

    st.markdown("""
    <p style='color:#b0b3c8; font-size:0.75rem; margin:0 0 1rem 0.5rem;'>
        Scoring = (Booking/Shift ÷ 1) × 100 × 30%
    </p>""", unsafe_allow_html=True)

    # ── Total ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style='background:#f5f6ff; border:1px solid #dde0f0; border-radius:12px;
        padding:1rem 1.2rem; display:flex; justify-content:space-between;
        align-items:center; margin-top:0.5rem;'>
        <span style='font-family:"Plus Jakarta Sans",sans-serif; font-weight:700;
            color:#3d3d5c;'>Total Score</span>
        <span style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1.3rem;
            font-weight:800; color:#5b52e8;'>{d["total_score"]:.1f}</span>
    </div>
    <div style='background:#f0f2ff; border:1px solid #c8ccf0; border-radius:12px;
        padding:1rem 1.2rem; display:flex; justify-content:space-between;
        align-items:center; margin-top:0.5rem;'>
        <span style='font-family:"Plus Jakarta Sans",sans-serif; font-weight:700;
            color:#3d3d5c;'>Diversified Channel Index (×25%)</span>
        <span style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1.5rem;
            font-weight:800; color:{div_color};'>{d["div_index"]:.1f}</span>
    </div>
    """, unsafe_allow_html=True)
