import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

SPREADSHEET_ID = "11fP61xXfqgP3KnXPbBRSd22YSzixKYPM7GPLHR4c6YQ"

# Daftar semua center — tambahkan center baru di sini
ALL_CENTERS = ["TBT", "KGD", "KLM", "BTR", "BTY", "BDM", "BAL", "SUN", "PKY", "PLM"]

# Center yang sudah punya sheet performance (untuk uji coba)
ACTIVE_CENTERS = ["BTR", "KGD", "KLM", "TBT", "BTY", "BDM"]


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300, show_spinner=False)
def get_sheet_df(sheet_name: str) -> pd.DataFrame:
    """Ambil sheet biasa (users, centers, targets) sebagai DataFrame."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_gspread_client()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                get_gspread_client.clear()
            else:
                st.error(f"Gagal mengambil data '{sheet_name}'. Cek koneksi internet.")
                return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_performance_df(center_code: str) -> pd.DataFrame:
    """
    Ambil sheet performance_[CENTER] yang strukturnya horizontal.
    Baris 1 = header kosong / nama EC
    Baris 2 = nama EC (Juan, Amanda, dst)
    Baris 3 = sub-header (tanggal, booking, show up, paid)
    Baris 4+ = data harian

    Return DataFrame panjang dengan kolom:
    tanggal | nama_ec | booking | show_up | paid | center
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_gspread_client()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(f"performance_{center_code}")
            raw = worksheet.get_all_values()
            return parse_performance_sheet(raw, center_code)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                get_gspread_client.clear()
            else:
                st.error(f"Gagal mengambil data performance_{center_code}.")
                return pd.DataFrame()


def clean_int(val) -> int:
    """Bersihkan nilai dari Google Sheets yang bisa berupa '3)', '3', atau ''."""
    if not val or str(val).strip() == "":
        return 0
    try:
        # Hapus semua karakter non-digit kecuali minus
        cleaned = ''.join(c for c in str(val) if c.isdigit() or c == '-')
        return int(cleaned) if cleaned else 0
    except:
        return 0


def parse_performance_sheet(raw: list, center_code: str) -> pd.DataFrame:
    """
    Parse sheet horizontal menjadi DataFrame panjang.
    Struktur sheet:
      Row 0: link
      Row 1: nama EC di col 0, 6, 12, 18, ... (setiap 6 kolom)
      Row 2: header (tanggal, booking, show up, paid) per grup
      Row 3+: data harian
    Nilai dari Google Sheets bisa berupa '3)', '0)', dll — perlu dibersihkan.
    """
    if len(raw) < 4:
        return pd.DataFrame()

    row_ec_names = raw[1]
    row_subheader = raw[2]
    data_rows = raw[3:]

    # Cari posisi grup EC berdasarkan header "tanggal"
    groups = []
    i = 0
    while i < len(row_subheader):
        subh = row_subheader[i].strip().lower()
        if subh == "tanggal":
            ec_name = row_ec_names[i].strip() if i < len(row_ec_names) else ""
            if ec_name:
                groups.append({
                    "nama_ec": ec_name,
                    "col_tanggal": i,
                    "col_booking": i + 1,
                    "col_showup":  i + 2,
                    "col_paid":    i + 3,
                })
            i += 4
        else:
            i += 1

    # Bangun DataFrame panjang
    records = []
    for row in data_rows:
        for g in groups:
            try:
                tanggal_raw = row[g["col_tanggal"]].strip() if g["col_tanggal"] < len(row) else ""
                if not tanggal_raw:
                    continue
                tanggal = pd.to_datetime(tanggal_raw, dayfirst=True, errors="coerce")
                if pd.isna(tanggal):
                    continue
                booking = clean_int(row[g["col_booking"]] if g["col_booking"] < len(row) else "")
                show_up = clean_int(row[g["col_showup"]]  if g["col_showup"]  < len(row) else "")
                paid    = clean_int(row[g["col_paid"]]    if g["col_paid"]    < len(row) else "")
                records.append({
                    "tanggal": tanggal,
                    "nama_ec": g["nama_ec"],
                    "booking": booking,
                    "show_up": show_up,
                    "paid":    paid,
                    "center":  center_code,
                })
            except Exception:
                continue

    return pd.DataFrame(records) if records else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_all_performance(centers: list = None) -> pd.DataFrame:
    """Gabungkan performance dari semua center aktif."""
    if centers is None:
        centers = ACTIVE_CENTERS
    dfs = []
    for c in centers:
        df = get_performance_df(c)
        if not df.empty:
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def clear_cache():
    st.cache_data.clear()
    get_gspread_client.clear()


def login_user(username: str, password: str):
    try:
        df = get_sheet_df("users")
        if df.empty:
            st.error("Tidak dapat terhubung ke database.")
            return None
        df.columns = df.columns.str.strip().str.lower()
        user = df[
            (df["username"].str.strip() == username.strip()) &
            (df["password"].astype(str).str.strip() == password.strip())
        ]
        if not user.empty:
            row = user.iloc[0]
            return {
                "username": row["username"],
                "password": row["password"],
                "role": row["role"].upper(),
                "nama_lengkap": row["nama_lengkap"],
                "center_id": row["center_id"],
            }
        return None
    except Exception as e:
        st.error(f"Error saat login: {e}")
        return None


def logout_user():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
