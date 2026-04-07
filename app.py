import streamlit as st
from auth import login_user, logout_user
from dashboard_ec import show_ec_dashboard
from dashboard_cm import show_cm_dashboard
from dashboard_ho import show_ho_dashboard

st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #eef0f8 !important;
    color: #1e1e2e !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #e8eaf6 0%, #eef0f8 50%, #e8f0fe 100%) !important;
}

[data-testid="stHeader"] { background: transparent !important; }

h1, h2, h3 { font-family: 'Plus Jakarta Sans', sans-serif !important; color: #1e1e2e !important; }

.stButton > button {
    background: linear-gradient(135deg, #5b52e8, #7c6ff7) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(91, 82, 232, 0.35) !important;
}

.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1.5px solid #c5c8e8 !important;
    border-radius: 10px !important;
    color: #1e1e2e !important;
    padding: 0.6rem 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
}
.stTextInput > div > div > input::placeholder {
    color: #9194b3 !important;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #5b52e8 !important;
    box-shadow: 0 0 0 3px rgba(91,82,232,0.15) !important;
    outline: none !important;
}
.stTextInput label {
    color: #3d3d5c !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

.stSelectbox > div > div {
    background: #ffffff !important;
    border: 1.5px solid #c5c8e8 !important;
    border-radius: 10px !important;
    color: #1e1e2e !important;
}
.stSelectbox label {
    color: #3d3d5c !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #dde0f0 !important;
    border-radius: 16px !important;
    padding: 1.2rem !important;
}

.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }

div[data-testid="stSidebarContent"] {
    background: #e4e6f4 !important;
    border-right: 1px solid #c5c8e8 !important;
}

.block-container { padding-top: 2rem !important; }

hr { border-color: #c5c8e8 !important; }

/* Sembunyikan status running */
[data-testid="stStatusWidget"] { display: none !important; }
.stSpinner { display: none !important; }
iframe[title="st_app_loading"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


def show_login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin-bottom: 2rem;'>
            <div style='font-size:3rem; margin-bottom:0.5rem;'>📊</div>
            <h1 style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1.8rem; font-weight:800;
                letter-spacing:-0.02em;
                background: linear-gradient(135deg, #5b52e8, #7c6ff7, #4a9eff);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; margin-bottom:0.3rem;'>
                Sales Dashboard
            </h1>
            <p style='color: #6b6f8e; font-size:0.9rem;'>
                Performance Monitoring System
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background: #ffffff; border: 1px solid #dde0f0;
            border-radius: 20px; padding: 2rem;
            box-shadow: 0 4px 24px rgba(91,82,232,0.08);'>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Login →", use_container_width=True):
            if username and password:
                result = login_user(username, password)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = result["username"]
                    st.session_state.role = result["role"]
                    st.session_state.nama = result["nama_lengkap"]
                    st.session_state.center_id = result["center_id"]
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah.")
            else:
                st.warning("⚠️ Mohon isi username dan password.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center; margin-top:1.5rem;
            color: #9194b3; font-size:0.8rem;'>
            EC · CM · HO Access Portal
        </div>
        """, unsafe_allow_html=True)


def show_topbar():
    role_colors = {"EC": "#2563eb", "CM": "#7c3aed", "HO": "#5b52e8"}
    role_color = role_colors.get(st.session_state.role, "#6c63ff")

    col1, col2, col3 = st.columns([5, 0.8, 0.8])
    with col1:
        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:1rem; margin-bottom:1rem;'>
            <div style='font-family:"Plus Jakarta Sans",sans-serif; font-size:1.4rem; font-weight:800;
                background: linear-gradient(135deg, #5b52e8, #7c6ff7);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text;'>📊 Sales Dashboard</div>
            <div style='background: {role_color}18; border: 1px solid {role_color}55;
                color: {role_color}; border-radius: 20px; padding: 0.2rem 0.8rem;
                font-size: 0.8rem; font-weight: 600;'>
                {st.session_state.role}
            </div>
            <div style='color: #6b6f8e; font-size:0.9rem;'>
                {st.session_state.nama}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            from auth import clear_cache
            clear_cache()
            st.rerun()
    with col3:
        if st.button("Logout", use_container_width=True):
            logout_user()
            st.rerun()

    st.markdown("<hr style='margin-bottom:1.5rem;'>", unsafe_allow_html=True)


# ── Main Router ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login_page()
else:
    show_topbar()
    role = st.session_state.role
    if role == "EC":
        show_ec_dashboard()
    elif role == "CM":
        show_cm_dashboard()
    elif role == "HO":
        show_ho_dashboard()
    else:
        st.error("Role tidak dikenali.")
