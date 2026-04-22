"""
div_channel.py — Kalkulasi Diversified Channel Score per EC per bulan
"""
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import re

SPREADSHEET_ID = "11fP61xXfqgP3KnXPbBRSd22YSzixKYPM7GPLHR4c6YQ"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

TARGET_BOOKING_PER_SHIFT = 1.0
TARGET_REFERRER_PCT      = 0.30
WEIGHT_CROSSSELL         = 0.50
WEIGHT_REFERRAL          = 0.20
WEIGHT_EVENT             = 0.30  # 30%
WEIGHT_DIV_CHANNEL       = 0.25

# Mapping nama bulan Indonesia/Inggris singkat ke angka
MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"mei":5,"may":5,
    "jun":6,"jul":7,"agu":8,"aug":8,"sep":9,"okt":10,"oct":10,
    "nov":11,"des":12,"dec":12
}


def _parse_date(val) -> datetime | None:
    """
    Parse berbagai format tanggal:
    - '1 Feb', '2 Feb 2026', '27-Feb-2026', '5-Jul-2025'
    - '16-Mar-2026', '2026-02-01', '45843' (serial Excel)
    """
    if not val or str(val).strip() == "":
        return None
    s = str(val).strip()

    # Format standard
    for fmt in ["%d-%b-%Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(s, fmt)
        except:
            pass

    # Format '1 Feb' atau '2 Feb' (tanpa tahun) — assume 2026
    m = re.match(r'^(\d{1,2})\s+([A-Za-z]+)$', s)
    if m:
        day = int(m.group(1))
        mon = MONTH_MAP.get(m.group(2).lower())
        if mon:
            return datetime(2026, mon, day)

    # Excel serial
    try:
        n = int(float(s))
        if 40000 < n < 60000:
            return datetime(1899, 12, 30) + timedelta(days=n)
    except:
        pass

    return None


def _in_month(val, year: int, month: int) -> bool:
    """Cek apakah tanggal berada dalam bulan tertentu DAN sebelum hari ini (H-1)."""
    dt = _parse_date(val)
    if dt is None:
        return False
    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    return dt.year == year and dt.month == month and dt <= yesterday


@st.cache_resource(show_spinner=False)
def _get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


def _get_raw(sheet_name: str) -> list:
    for attempt in range(3):
        try:
            client = _get_client()
            sh = client.open_by_key(SPREADSHEET_ID)
            ws = sh.worksheet(sheet_name)
            return ws.get_all_values()
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                raise e
    return []


@st.cache_data(ttl=300, show_spinner=False)
def _load_crosssell_shift() -> list:
    return _get_raw("crosssell_shift")

@st.cache_data(ttl=300, show_spinner=False)
def _load_crosssell_leads() -> list:
    return _get_raw("crosssell_leads")

@st.cache_data(ttl=300, show_spinner=False)
def _load_ref_reg() -> list:
    return _get_raw("ref_reg_database")

@st.cache_data(ttl=300, show_spinner=False)
def _load_ref_referral() -> list:
    return _get_raw("ref_referral")

@st.cache_data(ttl=300, show_spinner=False)
def _load_event_shift() -> list:
    return _get_raw("event_shift")

@st.cache_data(ttl=300, show_spinner=False)
def _load_event_leads() -> list:
    return _get_raw("crosssell_leads")  # sama sheet, filter beda


def calc_shift(ec_name: str, center: str, year: int, month: int) -> int:
    """
    Hitung shift dari crosssell_shift.
    Row 2: tanggal format '1 Feb', '2 Feb' dst (col 1+)
    Row 3+: center label atau nama EC dengan nilai 0/1
    """
    raw = _load_crosssell_shift()
    if not raw or len(raw) < 3:
        return 0

    date_row = raw[2]

    # Cari kolom yang sesuai bulan & tahun, hanya sampai H-1
    target_cols = []
    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    for ci, cell in enumerate(date_row):
        if ci == 0:
            continue
        s = cell.strip()
        if not s:
            continue
        dt = _parse_date(s)
        if dt is None:
            # Format '1 Feb' tanpa tahun
            m = re.match(r'^(\d{1,2})\s+([A-Za-z]+)$', s)
            if m:
                mon = MONTH_MAP.get(m.group(2).lower())
                day = int(m.group(1))
                if mon and mon == month:
                    dt_check = datetime(year, mon, day)
                    if dt_check <= yesterday:
                        target_cols.append(ci)
            continue
        if dt and dt.month == month and (dt.year == year or dt.year == 2026) and dt <= yesterday:
            target_cols.append(ci)

    if not target_cols:
        return 0

    # Cari baris EC dalam center yang benar
    in_center = False
    for row in raw[3:]:
        if not row or not row[0].strip():
            continue
        val0 = row[0].strip()
        if val0.upper() in ["BTR","KGD","KLM","TBT","BTY","BDM","BAL","SUN","PKY","PLM"]:
            in_center = (val0.upper() == center.upper())
            continue
        if in_center and val0.lower() == ec_name.lower():
            total = 0
            for ci in target_cols:
                if ci < len(row):
                    try:
                        total += int(row[ci])
                    except:
                        pass
            return total

    return 0


def calc_event_shift(ec_name: str, year: int, month: int) -> int:
    """
    Hitung shift Offline Event dari event_shift.
    Kolom A = tanggal, Kolom B = nama EC.
    Hitung baris yang col A ada di bulan tsb dan col B = ec_name.
    """
    raw = _load_event_shift()
    if not raw:
        return 0

    count = 0
    # Cari data row (skip header rows)
    data_start = 0
    for i, row in enumerate(raw[:5]):
        if row and str(row[0]).strip().lower() in ["tanggal", "date"]:
            data_start = i + 1
            break

    for row in raw[data_start:]:
        if not row or len(row) < 2:
            continue
        date_val = str(row[0]).strip()
        ec_val   = str(row[1]).strip()
        if (ec_val.lower() == ec_name.lower() and
            _in_month(date_val, year, month)):
            count += 1

    return count


def calc_event(ec_name: str, center: str, year: int, month: int) -> dict:
    """
    Hitung Leads, Booking OTS, Booking FU untuk Offline Event.
    Sama dengan crosssell tapi filter kolom D = 'Offline - Mall Booth' (atau mengandung).
    """
    raw = _load_crosssell_leads()
    if not raw:
        return {"leads": 0, "booking_ots": 0, "booking_fu": 0}

    header_idx = None
    for i, row in enumerate(raw):
        row_str = " ".join(str(c).lower() for c in row if c)
        if "first chat" in row_str or "ec/spg" in row_str:
            header_idx = i
            break

    if header_idx is None:
        return {"leads": 0, "booking_ots": 0, "booking_fu": 0}

    leads = 0
    booking_ots = 0
    booking_fu  = 0

    for row in raw[header_idx + 1:]:
        if not row or len(row) < 5:
            continue

        date_val   = str(row[0]).strip()
        ec_val     = str(row[1]).strip()
        branch_val = str(row[2]).strip()
        source_val = str(row[3]).strip()
        nohp_val   = str(row[4]).strip()
        ots_val    = str(row[5]).strip() if len(row) > 5 else ""
        type_val   = str(row[6]).strip() if len(row) > 6 else ""

        # Filter: EC, center, bulan, source = "Offline - Mall Booth"
        if (ec_val.lower() != ec_name.lower() or
            branch_val.upper() != center.upper() or
            "mall booth" not in source_val.lower() or
            not _in_month(date_val, year, month)):
            continue

        if nohp_val:
            leads += 1
            if type_val.lower() == "booking" and ots_val.lower() == "yes":
                booking_ots += 1
            elif type_val.lower() == "booking" and ots_val == "":
                booking_fu += 1

    return {"leads": leads, "booking_ots": booking_ots, "booking_fu": booking_fu}


def calc_crosssell(ec_name: str, center: str, year: int, month: int) -> dict:
    """
    Hitung Leads, Booking OTS, Booking FU dari crosssell_leads.
    Header di row 7 (0-indexed): First Chat Date, EC/SPG Name, Branch,
                                  Source Lead, No.HP, OTS or Not?, Leads Type
    Data mulai row 8.
    """
    raw = _load_crosssell_leads()
    if not raw:
        return {"leads": 0, "booking_ots": 0, "booking_fu": 0}

    # Cari header row
    header_idx = None
    for i, row in enumerate(raw):
        row_str = " ".join(str(c).lower() for c in row if c)
        if "first chat" in row_str or "ec/spg" in row_str:
            header_idx = i
            break

    if header_idx is None:
        return {"leads": 0, "booking_ots": 0, "booking_fu": 0}

    leads = 0
    booking_ots = 0
    booking_fu  = 0

    for row in raw[header_idx + 1:]:
        if not row or len(row) < 5:
            continue

        date_val    = str(row[0]).strip()   # col A
        ec_val      = str(row[1]).strip()   # col B
        branch_val  = str(row[2]).strip()   # col C
        source_val  = str(row[3]).strip()   # col D
        nohp_val    = str(row[4]).strip()   # col E
        ots_val     = str(row[5]).strip() if len(row) > 5 else ""  # col F
        type_val    = str(row[6]).strip() if len(row) > 6 else ""  # col G

        # Filter: EC name, center, bulan, source "offline"
        if (ec_val.lower() != ec_name.lower() or
            branch_val.upper() != center.upper() or
            "offline" not in source_val.lower() or
            not _in_month(date_val, year, month)):
            continue

        # Leads: no_hp tidak blank
        if nohp_val:
            leads += 1

            # Booking OTS: type=Booking, ots=Yes
            if type_val.lower() == "booking" and ots_val.lower() == "yes":
                booking_ots += 1
            # Booking FU: type=Booking, ots blank
            elif type_val.lower() == "booking" and ots_val == "":
                booking_fu += 1

    return {"leads": leads, "booking_ots": booking_ots, "booking_fu": booking_fu}


def calc_referral_showup(ec_name: str, center: str, year: int, month: int) -> int:
    """
    Hitung Show Up dari ref_reg_database.
    Header di row 3: Date, Nama EC, Branch, Show Up
    Data mulai row 4.
    """
    raw = _load_ref_reg()
    if not raw:
        return 0

    count = 0
    for row in raw[4:]:
        if not row or len(row) < 4:
            continue
        date_val   = str(row[0]).strip()
        ec_val     = str(row[1]).strip()
        center_val = str(row[2]).strip()
        showup_val = str(row[3]).strip()

        if (ec_val.lower() == ec_name.lower() and
            center_val.upper() == center.upper() and
            showup_val.lower() == "yes" and
            _in_month(date_val, year, month)):
            count += 1

    return count


def calc_referrer(ec_name: str, center: str, year: int, month: int) -> int:
    """
    Hitung Referrer unik dari ref_referral.
    Header di row 4: Date, EC Name, Center Code, No HP
    Data mulai row 5.
    """
    raw = _load_ref_referral()
    if not raw:
        return 0

    # Cari header row
    data_start = 5  # default
    for i, row in enumerate(raw):
        row_str = " ".join(str(c).lower() for c in row if c)
        if "ec name" in row_str or "center code" in row_str:
            data_start = i + 1
            break

    unique_hp = set()
    for row in raw[data_start:]:
        if not row or len(row) < 4:
            continue
        date_val   = str(row[0]).strip()
        ec_val     = str(row[1]).strip()
        center_val = str(row[2]).strip()
        hp_val     = str(row[3]).strip()

        if (ec_val.lower() == ec_name.lower() and
            center_val.upper() == center.upper() and
            hp_val != "" and
            _in_month(date_val, year, month)):
            unique_hp.add(hp_val)

    return len(unique_hp)


def calc_div_channel(ec_name: str, center: str, year: int, month: int) -> dict:
    """Hitung Diversified Channel Score lengkap."""
    # 1. Cross Sell Offline
    shift         = calc_shift(ec_name, center, year, month)
    cs            = calc_crosssell(ec_name, center, year, month)
    cs_leads      = cs["leads"]
    cs_bots       = cs["booking_ots"]
    cs_bfu        = cs["booking_fu"]
    cs_total      = cs_bots + cs_bfu
    cs_bps        = round(cs_total / shift, 2) if shift > 0 else 0.0
    cs_score      = round((cs_bps / TARGET_BOOKING_PER_SHIFT) * 100 * WEIGHT_CROSSSELL, 2)

    # 2. Referral Trial Day
    showup    = calc_referral_showup(ec_name, center, year, month)
    referrer  = calc_referrer(ec_name, center, year, month)
    ref_pct   = round(referrer / showup, 4) if showup > 0 else 0.0
    ref_score = round((ref_pct / TARGET_REFERRER_PCT) * 100 * WEIGHT_REFERRAL, 2)

    # 3. Offline Event
    ev_shift  = calc_event_shift(ec_name, year, month)
    ev        = calc_event(ec_name, center, year, month)
    ev_leads  = ev["leads"]
    ev_bots   = ev["booking_ots"]
    ev_bfu    = ev["booking_fu"]
    ev_total  = ev_bots + ev_bfu
    ev_bps    = round(ev_total / ev_shift, 2) if ev_shift > 0 else 0.0
    ev_score  = round((ev_bps / TARGET_BOOKING_PER_SHIFT) * 100 * WEIGHT_EVENT, 2)

    total_score = round(cs_score + ref_score + ev_score, 2)
    div_index   = round(total_score * WEIGHT_DIV_CHANNEL, 2)

    return {
        "ec_name": ec_name, "center": center, "year": year, "month": month,
        # Cross Sell Offline
        "cs_shift": shift, "cs_leads": cs_leads,
        "cs_booking_ots": cs_bots, "cs_booking_fu": cs_bfu,
        "cs_total_booking": cs_total,
        "cs_booking_per_shift": cs_bps, "cs_score": cs_score,
        # Referral Trial Day
        "ref_showup": showup, "ref_referrer": referrer,
        "ref_pct": ref_pct, "ref_score": ref_score,
        # Offline Event
        "ev_shift": ev_shift, "ev_leads": ev_leads,
        "ev_booking_ots": ev_bots, "ev_booking_fu": ev_bfu,
        "ev_total_booking": ev_total,
        "ev_booking_per_shift": ev_bps, "ev_score": ev_score,
        # Total
        "total_score": total_score, "div_index": div_index,
    }
