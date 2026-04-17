"""
wow_mom_loader.py — Baca data dari sheet wow_mom_data untuk chart WoW & MoM
"""
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import re

SPREADSHEET_ID = "11fP61xXfqgP3KnXPbBRSd22YSzixKYPM7GPLHR4c6YQ"

CENTER_ROWS = {
    "BTR": 2, "KGD": 11, "KLM": 20,
    "TBT": 29, "BTY": 38, "BDM": 47,
}

MOM_COLS      = {"JAN": 0, "FEB": 1, "MAR": 2, "APR": 3}
MOM_MONTH_NUM = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4}
WOW_COL_START = 35


def get_val(cell) -> str:
    if cell is None: return ""
    s = str(cell)
    if "COMPUTED_VALUE" in s or "DUMMYFUNCTION" in s:
        m = re.search(r'\),(.+?)(?:"\)|\)$|$)', s)
        if m:
            return m.group(1).strip().strip('"').strip("'").strip()
        return ""
    return s.strip()


def safe_int(val) -> int:
    try:
        v = get_val(val) if not isinstance(val, (int, float)) else str(int(val))
        cleaned = ''.join(c for c in str(v) if c.isdigit() or c == '-')
        return int(cleaned) if cleaned else 0
    except:
        return 0


@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300, show_spinner=False)
def load_wow_mom_raw() -> list:
    for attempt in range(3):
        try:
            client = _get_gspread_client()
            sh = client.open_by_key(SPREADSHEET_ID)
            ws = sh.worksheet("wow_mom_data")
            return ws.get_all_values()
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                st.error(f"Gagal membaca wow_mom_data: {e}")
                return []


def _parse_center(raw: list, center: str) -> dict:
    start       = CENTER_ROWS[center]
    header_row  = start + 1
    booking_row = start + 2
    showup_row  = start + 3
    paid_row    = start + 4

    if len(raw) <= paid_row:
        return {}

    r_header  = raw[header_row]
    r_booking = raw[booking_row]
    r_showup  = raw[showup_row]
    r_paid    = raw[paid_row]

    def rv(row, col):
        return safe_int(row[col]) if col < len(row) else 0

    # MoM
    mom_rows = []
    for mname, cidx in MOM_COLS.items():
        bk = rv(r_booking, cidx)
        su = rv(r_showup,  cidx)
        pd_ = rv(r_paid,   cidx)
        mom_rows.append({
            "label":      mname,
            "month_num":  MOM_MONTH_NUM[mname],
            "booking":    bk,
            "show_up":    su,
            "paid":       pd_,
            "showup_pct": round(su  / bk  * 100, 1) if bk  > 0 else 0.0,
            "paid_pct":   round(pd_ / su  * 100, 1) if su  > 0 else 0.0,
        })

    # WoW
    wow_rows = []
    col = WOW_COL_START
    while col < len(r_header):
        wlabel = get_val(r_header[col])
        if not wlabel or not wlabel.startswith("Week"):
            break
        wnum = int(wlabel.replace("Week", "").strip())
        bk  = rv(r_booking, col)
        su  = rv(r_showup,  col)
        pd_ = rv(r_paid,    col)
        wow_rows.append({
            "label":      f"W{wnum:02d}",
            "week_num":   wnum,
            "booking":    bk,
            "show_up":    su,
            "paid":       pd_,
            "showup_pct": round(su  / bk  * 100, 1) if bk  > 0 else 0.0,
            "paid_pct":   round(pd_ / su  * 100, 1) if su  > 0 else 0.0,
        })
        col += 1

    return {
        "mom": pd.DataFrame(mom_rows),
        "wow": pd.DataFrame(wow_rows),
    }


def get_trend_data(centers: list = None) -> dict:
    """
    Ambil dan agregat data MoM & WoW dari wow_mom_data.
    centers: list center yang ingin diagregat, None = semua
    Return: {"mom": DataFrame, "wow": DataFrame}
    """
    if centers is None:
        centers = list(CENTER_ROWS.keys())

    raw = load_wow_mom_raw()
    if not raw:
        return {}

    today      = datetime.now()
    today_month = today.month
    today_week  = today.isocalendar()[1]

    all_mom, all_wow = [], []

    for center in centers:
        if center not in CENTER_ROWS:
            continue
        data = _parse_center(raw, center)
        if not data:
            continue

        df_mom = data["mom"].copy()
        df_mom = df_mom[df_mom["month_num"] <= today_month]
        df_mom["center"] = center
        all_mom.append(df_mom)

        df_wow = data["wow"].copy()
        df_wow = df_wow[
            (df_wow["booking"] > 0) &
            (df_wow["week_num"] <= today_week)
        ]
        df_wow["center"] = center
        all_wow.append(df_wow)

    def agg_df(frames, group_col, sort_col):
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        agg = combined.groupby([group_col, sort_col]).agg(
            booking=("booking", "sum"),
            show_up=("show_up", "sum"),
            paid=("paid", "sum"),
        ).reset_index().sort_values(sort_col)
        agg["showup_pct"] = agg.apply(
            lambda r: round(r["show_up"] / r["booking"] * 100, 1) if r["booking"] > 0 else 0.0, axis=1)
        agg["paid_pct"] = agg.apply(
            lambda r: round(r["paid"] / r["show_up"] * 100, 1) if r["show_up"] > 0 else 0.0, axis=1)
        return agg

    return {
        "mom": agg_df(all_mom, "label", "month_num"),
        "wow": agg_df(all_wow, "label", "week_num"),
    }
