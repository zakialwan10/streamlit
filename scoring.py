import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# ── Konstanta ────────────────────────────────────────────────────────────────
TARGETS = {
    "paid_cvr":    0.65,
    "fp_sameday":  0.60,
    "m0":          0.70,
    "m1":          0.90,
    "m2":          0.95,
    "diversified": 100.0,
}
WEIGHTS = {
    "paid_cvr":    0.35,
    "fp_sameday":  0.20,
    "m0":          0.10,
    "m1":          0.05,
    "m2":          0.05,
    "diversified": 0.25,
}

# Posisi kolom FIXED berdasarkan analisis file Excel
# (Jan, Feb, Mar) untuk setiap metric
METRIC_COLS = {
    "paid_cvr":    {"Jan": 32, "Feb": 33, "Mar": 34},
    "fp_sameday":  {"Jan": 36, "Feb": 37, "Mar": 38},
    "m0":          {"Jan": 40, "Feb": 41, "Mar": 42},
    "m1":          {"Jan": 44, "Feb": 45, "Mar": 46},
    "m2":          {"Jan": 48, "Feb": 49, "Mar": 50},
    "diversified": {"Jan": 52, "Feb": 53, "Mar": 54},
}
EC_COL  = 1
LOC_COL = 2
DATA_START_ROW = 6  # index 6 = baris ke-7 (0-indexed)


def get_category(score: float) -> tuple:
    if score == 0:
        return ("", "#6b6f8e")
    elif score >= 85:
        return ("Good Standing", "#059669")
    elif score >= 75:
        return ("Coaching & Re-training Required", "#d97706")
    else:
        return ("4-6 Weeks PIP", "#dc2626")


def safe_float(val) -> float:
    """
    Konversi nilai ke float.
    Google Sheets API mengembalikan string '72%' untuk persentase.
    Diversified adalah angka mentah '115'.
    """
    if val is None or val == '':
        return 0.0
    s = str(val).strip()
    if s.endswith('%'):
        try:
            return float(s.replace('%', '')) / 100.0
        except:
            return 0.0
    try:
        return float(s)
    except:
        return 0.0


def compute_score(paid_cvr, fp_sameday, m0, m1, m2, diversified) -> dict:
    metrics = {
        "paid_cvr":    (paid_cvr,    TARGETS["paid_cvr"],    WEIGHTS["paid_cvr"]),
        "fp_sameday":  (fp_sameday,  TARGETS["fp_sameday"],  WEIGHTS["fp_sameday"]),
        "m0":          (m0,          TARGETS["m0"],          WEIGHTS["m0"]),
        "m1":          (m1,          TARGETS["m1"],          WEIGHTS["m1"]),
        "m2":          (m2,          TARGETS["m2"],          WEIGHTS["m2"]),
        "diversified": (diversified, TARGETS["diversified"], WEIGHTS["diversified"]),
    }
    result = {}
    total = 0.0
    for key, (achievement, target, weight) in metrics.items():
        # Score TIDAK di-cap 100 — sesuai formula Google Sheets
        score = (achievement / target) * 100 if target != 0 else 0
        final = score * weight
        result[key] = {
            "achievement": achievement,
            "score": round(score, 1),
            "final": round(final, 1)
        }
        total += final
    result["total"] = round(total, 1)
    cat, color = get_category(total)
    result["category"] = cat
    result["category_color"] = color
    return result


@st.cache_data(ttl=300, show_spinner=False)
def load_all_ec_scores() -> pd.DataFrame:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    for attempt in range(3):
        try:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES
            )
            client = gspread.authorize(creds)
            sh = client.open_by_key("11fP61xXfqgP3KnXPbBRSd22YSzixKYPM7GPLHR4c6YQ")
            ws = sh.worksheet("all_ec_performance")
            raw = ws.get_all_values()
            return parse_scores(raw)
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                st.error(f"Gagal membaca all_ec_performance: {e}")
                return pd.DataFrame()


def parse_scores(raw: list) -> pd.DataFrame:
    records = []
    for row in raw[DATA_START_ROW:]:
        # Pad row jika kurang panjang
        while len(row) <= 54:
            row.append("")

        ec_name  = str(row[EC_COL]).strip()
        location = str(row[LOC_COL]).strip()
        if not ec_name:
            continue

        for month in ["Jan", "Feb", "Mar"]:
            vals = {}
            has_data = False
            for metric_key, month_map in METRIC_COLS.items():
                col = month_map[month]
                raw_val = row[col] if col < len(row) else ""
                v = safe_float(raw_val)
                vals[metric_key] = v
                if v > 0:
                    has_data = True

            if not has_data:
                continue

            sc = compute_score(
                vals["paid_cvr"],
                vals["fp_sameday"],
                vals["m0"],
                vals["m1"],
                vals["m2"],
                vals["diversified"],
            )

            records.append({
                "ec_name":       ec_name,
                "location":      location,
                "bulan":         month,
                "paid_cvr":      vals["paid_cvr"],
                "fp_sameday":    vals["fp_sameday"],
                "m0":            vals["m0"],
                "m1":            vals["m1"],
                "m2":            vals["m2"],
                "diversified":   vals["diversified"],
                "total_score":   sc["total"],
                "category":      sc["category"],
                "category_color":sc["category_color"],
                "score_detail":  sc,
            })

    return pd.DataFrame(records)


def get_ec_score(ec_name: str, bulan: str, df_scores: pd.DataFrame = None) -> dict:
    if df_scores is None:
        df_scores = load_all_ec_scores()
    if df_scores is None or df_scores.empty:
        return None
    row = df_scores[
        (df_scores["ec_name"].str.strip().str.lower() == ec_name.strip().lower()) &
        (df_scores["bulan"] == bulan)
    ]
    if row.empty:
        return None
    return row.iloc[0].to_dict()
