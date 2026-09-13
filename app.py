import hashlib
import json
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data.sample_equipment import SAMPLE_EQUIPMENT
from src.advisor import get_lifecycle_recommendation
from src.ai_explanation import generate_ai_explanation
from src.assessment_history import (
    clear_assessment_history,
    load_assessment_history,
    save_assessment,
)
from src.dashboard import build_dashboard_stats
from src.priority_assessment import assess_equipment_priority
from src.report_generator import generate_assessment_report


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
USERS_FILE = DATA_DIR / "users.json"
ROLE_OPTIONS = ["Biomedical Engineer", "Equipment Manager"]


def build_header_markup():
    return f"""
    <div class=\"app-header\">
        <div class=\"app-header-content\">
            <div class=\"app-header-text\">
                <h1>AI-Based Biomedical Equipment Life-Cycle Advisor</h1>
                <p>A simple decision-support interface for biomedical equipment planning.</p>
            </div>
        </div>
    </div>
    """


def get_recommendation_action(recommendation_label):
    action_map = {
        "Continue Assessment": "Continue routine monitoring and schedule the next planned review.",
        "Maintenance Assessment": "Schedule preventive maintenance and confirm the equipment remains fit for service.",
        "Repair Assessment": "Arrange a focused repair review and assess cost, reliability, and safety before returning the equipment to service.",
        "Refurbishment Consideration": "Evaluate refurbishment and requalification options to extend the equipment's useful life.",
        "Reuse Consideration": "Consider reuse only after a professional assessment confirms the equipment still meets operational needs.",
        "End-of-Life Review": "Begin an end-of-life review and plan responsible retirement, replacement, or disposal in line with local policy.",
    }
    return action_map.get(
        recommendation_label,
        "Review the equipment with the current operating team and follow the standard lifecycle guidance.",
    )


def build_demo_users():
    return {
        "biomedical_engineer": {
            "role": "Biomedical Engineer",
            "password_hash": hashlib.sha256("biomed123".encode()).hexdigest(),
        },
        "equipment_manager": {
            "role": "Equipment Manager",
            "password_hash": hashlib.sha256("manager123".encode()).hexdigest(),
        },
    }


def ensure_users_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps(build_demo_users(), indent=2), encoding="utf-8")


def load_users():
    ensure_users_file()

    try:
        file_users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        file_users = {}

    users = build_demo_users()
    if isinstance(file_users, dict):
        users.update(file_users)

    return users



def save_users(users):
    ensure_users_file()
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def verify_login(username, password):
    username = username.strip()
    if not username or not password:
        return None

    users = load_users()
    user = users.get(username)
    if not user:
        return None

    provided_hash = hashlib.sha256(password.encode()).hexdigest()
    if provided_hash != user.get("password_hash"):
        return None

    return user


def register_user(username, password, confirm_password, role):
    username = username.strip()

    if not username:
        return {"success": False, "message": "Username is required."}

    if not password:
        return {"success": False, "message": "Password is required."}

    if password != confirm_password:
        return {"success": False, "message": "Passwords do not match."}

    users = load_users()
    if username in users:
        return {
            "success": False,
            "message": "That username already exists. Please choose a different username.",
        }

    if role not in ROLE_OPTIONS:
        return {"success": False, "message": "Invalid role selected."}

    users[username] = {
        "role": role,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
    }
    save_users(users)

    return {
        "success": True,
        "message": f"Account created for {username}. You can now log in.",
    }


st.set_page_config(
    page_title="AI-Based Biomedical Equipment Life-Cycle Advisor",
    page_icon="🩺",
)

st.markdown(
    """
    <style>
        .stApp {
            background:
                linear-gradient(180deg, rgba(236, 247, 255, 0.97) 0%, rgba(248, 252, 255, 0.99) 100%),
                radial-gradient(circle at 15% 15%, rgba(38, 155, 167, 0.10), transparent 22%),
                radial-gradient(circle at 80% 5%, rgba(39, 107, 160, 0.10), transparent 24%),
                linear-gradient(120deg, rgba(12, 97, 125, 0.04) 0%, rgba(42, 157, 143, 0.05) 100%);
            background-attachment: fixed;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .app-header {
            background: linear-gradient(135deg, #0f4c81 0%, #0ea5a4 100%);
            border-radius: 18px;
            padding: 1.5rem 1.5rem 1rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 8px 24px rgba(15, 76, 129, 0.15);
            overflow: hidden;
        }
        .app-header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }
        .app-header-text {
            flex: 1 1 auto;
            min-width: 0;
        }
        .app-header h1 {
            color: #ffffff !important;
            margin: 0;
            font-size: 2.1rem;
            font-weight: 700;
        }
        .app-header p {
            color: rgba(255, 255, 255, 0.9);
            margin-top: 0.5rem;
            margin-bottom: 0;
            font-size: 1rem;
        }
        h2, h3 {
            color: #0f172a;
        }
        .stSubheader {
            color: #0f172a;
            font-weight: 700;
        }
        .stButton > button {
            background: linear-gradient(135deg, #0f4c81 0%, #0ea5a4 100%);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 0.45rem 1rem;
            font-weight: 600;
            box-shadow: 0 6px 14px rgba(15, 76, 129, 0.2);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #0b3d6b 0%, #0c8d8a 100%);
            box-shadow: 0 8px 18px rgba(15, 76, 129, 0.25);
        }
        .stDownloadButton > button {
            background: linear-gradient(135deg, #0f4c81 0%, #0ea5a4 100%);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 0.45rem 1rem;
            font-weight: 600;
            box-shadow: 0 6px 14px rgba(15, 76, 129, 0.2);
        }
        .stSuccess, .stInfo, .stWarning, .stError {
            border-radius: 12px;
            padding: 0.8rem 1rem;
            box-shadow: 0 4px 14px rgba(15, 76, 129, 0.08);
        }
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(236, 247, 255, 0.96) 0%, rgba(247, 251, 255, 0.98) 100%),
                radial-gradient(circle at 22% 18%, rgba(42, 157, 143, 0.08), transparent 25%);
            border-right: 1px solid #d8ebf7;
        }
        .sidebar-brand {
            background: linear-gradient(135deg, #0f4c81 0%, #0ea5a4 100%);
            border-radius: 16px;
            padding: 1rem 0.9rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 20px rgba(15, 76, 129, 0.15);
        }
        .sidebar-brand-top,
        .sidebar-brand-bottom {
            color: #ffffff;
            font-weight: 800;
            letter-spacing: 0.06em;
            line-height: 1.1;
            text-align: center;
        }
        .sidebar-brand-top {
            font-size: 1.15rem;
        }
        .sidebar-brand-bottom {
            font-size: 1.15rem;
        }
        .sidebar-brand-subtitle {
            margin-top: 0.5rem;
            text-align: center;
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.76rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .sidebar-section {
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid #d8ebf7;
            border-radius: 12px;
            padding: 0.85rem 0.9rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 4px 12px rgba(15, 76, 129, 0.06);
        }
        .sidebar-section-title {
            color: #0f4c81;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }
        .sidebar-profile-row {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.3rem 0;
            font-size: 0.9rem;
        }
        .sidebar-label {
            color: #475569;
            font-weight: 600;
        }
        .sidebar-value {
            color: #0f172a;
            font-weight: 700;
            text-align: right;
        }
        .sidebar-nav-item {
            display: block;
            background: #f8fbff;
            border: 1px solid #d8ebf7;
            border-radius: 10px;
            padding: 0.55rem 0.7rem;
            margin: 0.3rem 0;
            color: #0f172a;
            font-weight: 600;
            font-size: 0.9rem;
            text-decoration: none;
        }
        .sidebar-nav-item:hover {
            background: #edf6ff;
            border-color: #bfdff2;
            text-decoration: none;
        }
        .sidebar-divider {
            border-top: 1px solid #cfe3f0;
            margin: 0.85rem 0;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid #d8ebf7;
            border-radius: 14px;
            padding: 0.75rem;
            box-shadow: 0 4px 12px rgba(15, 76, 129, 0.08);
        }
        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }
        .result-card {
            background: linear-gradient(135deg, #f0f9ff 0%, #f9fcff 100%);
            border: 1px solid #c3deee;
            border-radius: 18px;
            padding: 1.25rem;
            box-shadow: 0 8px 24px rgba(15, 76, 129, 0.12);
            margin-bottom: 1rem;
        }
        .result-card p,
        .result-card ul,
        .result-card li {
            color: #1f2937;
            line-height: 1.6;
        }
        .result-card ul {
            margin: 0.4rem 0 0 1.1rem;
            padding-left: 0.75rem;
        }
        .result-label {
            color: #0f4c81;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .result-title {
            font-size: 2rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0.5rem;
        }
        .result-action {
            color: #0f172a;
            font-size: 1rem;
            line-height: 1.5;
        }
        .section-card {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #d4eaf6;
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 4px 14px rgba(15, 76, 129, 0.07);
            margin-bottom: 1rem;
        }
        .section-card p {
            margin: 0;
            color: #1f2937;
            line-height: 1.6;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 0.85rem;
        }
        .info-item {
            background: #f8fbff;
            border: 1px solid #d8ebf7;
            border-radius: 10px;
            padding: 0.8rem;
        }
        .info-label {
            display: inline-block;
            color: #0f4c81;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .stable-chart-container {
            margin-top: 0.75rem;
            margin-bottom: 0;
            display: block;
            padding: 0;
        }
        [data-testid="stVegaLiteChart"] {
            margin-top: 0.75rem !important;
            height: 240px !important;
            min-height: 240px !important;
            max-height: 240px !important;
        }
        [data-testid="stVegaLiteChart"] > div {
            height: 100% !important;
            min-height: 240px !important;
            max-height: 240px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None
if "logged_in_role" not in st.session_state:
    st.session_state["logged_in_role"] = None

if not st.session_state["authenticated"]:
    st.markdown(build_header_markup(), unsafe_allow_html=True)
    st.subheader("Login")
    st.markdown(
        "Privacy notice: This prototype uses a local account system with hashed password storage only. "
        "It is intended for demo use and should not be considered production-grade authentication."
    )

    if st.session_state.get("registration_message"):
        st.success(st.session_state.pop("registration_message"))

    auth_mode = st.radio(
        "Select an action",
        ["Log in", "Create New Account"],
        horizontal=True,
    )

    if auth_mode == "Create New Account":
        with st.form("registration_form"):
            registration_username = st.text_input("Username", key="registration_username")
            registration_password = st.text_input(
                "Password",
                type="password",
                key="registration_password",
            )
            registration_confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="registration_confirm_password",
            )
            registration_role = st.selectbox("Role", ROLE_OPTIONS, key="registration_role")
            register_submitted = st.form_submit_button("Create Account")

        if register_submitted:
            registration_result = register_user(
                registration_username,
                registration_password,
                registration_confirm_password,
                registration_role,
            )

            if registration_result["success"]:
                st.session_state["registration_message"] = registration_result["message"]
                st.session_state["login_username"] = registration_username
                st.rerun()
            else:
                st.error(registration_result["message"])
    else:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            user = verify_login(username, password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["logged_in_user"] = username
                st.session_state["logged_in_role"] = user["role"]
                st.rerun()
            else:
                st.error("Invalid username or password. Please use a valid demo or registered account.")

    st.stop()

st.markdown(build_header_markup(), unsafe_allow_html=True)
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-brand-top">BIOMEDICAL</div>
        <div class="sidebar-brand-bottom">LIFECYCLE</div>
        <div class="sidebar-brand-subtitle">Equipment Decision Support</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <div class="sidebar-section-title">USER PROFILE</div>
        <div class="sidebar-profile-row">
            <span class="sidebar-label">Username</span>
            <span class="sidebar-value">{}</span>
        </div>
        <div class="sidebar-profile-row">
            <span class="sidebar-label">Role</span>
            <span class="sidebar-value">{}</span>
        </div>
    </div>
    """.format(st.session_state["logged_in_user"], st.session_state["logged_in_role"]),
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <div class="sidebar-section-title">QUICK NAVIGATION</div>
        <a href="#1-equipment-information" class="sidebar-nav-item">Assessment</a>
        <a href="#sustainability-dashboard" class="sidebar-nav-item">Sustainability Dashboard</a>
        <a href="#assessment-history" class="sidebar-nav-item">Assessment History</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["logged_in_user"] = None
    st.session_state["logged_in_role"] = None
    st.rerun()

st.success(f"Logged in as {st.session_state['logged_in_role']} ({st.session_state['logged_in_user']})")

st.markdown(
    "This tool supports sustainable management of biomedical equipment in alignment with SDG 12 – Responsible Consumption and Production."
)

category_options = ["Imaging", "Monitor", "Ventilator", "Laboratory Analyzer", "Other"]
equipment_name_options = [item["equipment_name"] for item in SAMPLE_EQUIPMENT]

if "equipment_name" not in st.session_state:
    st.session_state["equipment_name"] = equipment_name_options[0]

selected_equipment = next(
    (item for item in SAMPLE_EQUIPMENT if item["equipment_name"] == st.session_state["equipment_name"]),
    SAMPLE_EQUIPMENT[0],
)

with st.form("equipment_form"):
    st.subheader("1. Equipment Information")

    equipment_name = st.selectbox(
        "Equipment name",
        equipment_name_options,
        index=equipment_name_options.index(st.session_state["equipment_name"])
        if st.session_state["equipment_name"] in equipment_name_options
        else 0,
        key="equipment_name",
    )

    equipment_category = st.selectbox(
        "Equipment category",
        category_options,
        index=(
            category_options.index(selected_equipment.get("category"))
            if selected_equipment.get("category") in category_options
            else category_options.index("Other")
        ),
    )
    age_years = st.slider("Age", min_value=0, max_value=20, value=5)
    current_condition = st.radio(
        "Current condition",
        ["Excellent", "Good", "Fair", "Poor"],
        horizontal=True,
    )

    st.subheader("2. Maintenance & Lifecycle Information")

    known_issue = st.text_area("Known issue/problem")

    last_maintenance = st.selectbox(
        "Last Maintenance",
        ["Within 6 months", "6–12 months ago", "More than 1 year ago", "Never / Unknown"],
    )
    manufacturer_support = st.selectbox(
        "Manufacturer Support",
        ["Available", "Limited", "Not available", "Unknown"],
    )
    usage_intensity = st.selectbox(
        "Usage Intensity",
        ["Low", "Moderate", "High"],
    )

    submitted = st.form_submit_button("Get Sustainability Recommendation")


if submitted:
    missing_fields = []

    if not equipment_name.strip():
        missing_fields.append("Equipment name")
    if not known_issue.strip():
        missing_fields.append("Known issue/problem")
    if age_years < 0:
        missing_fields.append("Age")

    if missing_fields:
        st.warning(
            "Please complete the required information before requesting a recommendation: "
            + ", ".join(missing_fields)
            + "."
        )
    else:
        if last_maintenance == "Within 6 months":
            maintenance_history = "Strong"
        elif last_maintenance == "6–12 months ago":
            maintenance_history = "Moderate"
        else:
            maintenance_history = "Weak"

        recommendation = get_lifecycle_recommendation(
            equipment_type=equipment_category,
            age_years=age_years,
            condition=current_condition,
            maintenance_history=maintenance_history,
            equipment_name=equipment_name,
            known_issue=known_issue,
            last_maintenance=last_maintenance,
            manufacturer_support=manufacturer_support,
            usage_intensity=usage_intensity,
        )

        priority_result = assess_equipment_priority(
            age_years=age_years,
            condition=current_condition,
            known_issue=known_issue,
        )
        recommendation_action = get_recommendation_action(recommendation["recommendation"])

        st.markdown("### ASSESSMENT RESULT")
        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">Assessment Result</div>
                <div class="result-title">{recommendation['recommendation']}</div>
                <div class="result-action"><strong>Action:</strong> {recommendation_action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### PRIORITY")
        st.markdown(
            f"""
            <div class="result-card">
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Priority</span><br>
                        <strong>{priority_result['priority']}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Reason</span><br>
                        {priority_result['reason']}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### KEY FACTORS CONSIDERED")
        key_factors_html = "".join(
            [
                f"<div class='info-item'><span class='info-label'>Equipment name</span><br>{equipment_name}</div>",
                f"<div class='info-item'><span class='info-label'>Equipment category</span><br>{equipment_category}</div>",
                f"<div class='info-item'><span class='info-label'>Age</span><br>{age_years} years</div>",
                f"<div class='info-item'><span class='info-label'>Current condition</span><br>{current_condition}</div>",
                f"<div class='info-item'><span class='info-label'>Known issue/problem</span><br>{known_issue}</div>",
                f"<div class='info-item'><span class='info-label'>Maintenance status</span><br>{maintenance_history}</div>",
                f"<div class='info-item'><span class='info-label'>Last maintenance</span><br>{last_maintenance}</div>",
                f"<div class='info-item'><span class='info-label'>Manufacturer support</span><br>{manufacturer_support}</div>",
            ]
        )
        st.markdown(
            f"""
            <div class="result-card">
                <div class="info-grid">
                    {key_factors_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### RECOMMENDED ACTION")
        st.markdown(
            f"""
            <div class="result-card">
                <p>{recommendation_action}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### SUSTAINABILITY BENEFIT")
        st.markdown(
            """
            <div class="result-card">
                <p>This recommendation supports responsible biomedical equipment lifecycle management by encouraging timely review, practical maintenance, and careful reuse or replacement decisions.</p>
                <p>It aligns with SDG 12 by helping extend useful equipment life where appropriate and reducing unnecessary early disposal.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### DISCLAIMER")
        st.warning(recommendation["decision_support_note"])

        st.markdown("### AI EXPLANATION")
        explanation_details = {
            "equipment_name": equipment_name,
            "equipment_type": equipment_category,
            "age_years": age_years,
            "condition": current_condition,
            "known_issue": known_issue,
            "last_maintenance": last_maintenance,
            "manufacturer_support": manufacturer_support,
            "usage_intensity": usage_intensity,
        }
        explanation = generate_ai_explanation(explanation_details, recommendation)

        recommendation_meaning = {
            "Continue Assessment": "The equipment currently appears suitable for continued monitoring and routine upkeep.",
            "Maintenance Assessment": "The equipment should be reviewed with maintenance support to keep it reliable and ready for service.",
            "Repair Assessment": "The equipment should be assessed for a practical repair path before further operational use.",
            "Refurbishment Consideration": "The equipment may benefit from refurbishment and requalification to extend its useful life.",
            "Reuse Consideration": "The equipment may be suitable for reuse after a professional check confirms it still meets operational needs.",
            "End-of-Life Review": "The equipment should be reviewed for responsible retirement, replacement, or disposal planning.",
        }

        factors_html = "".join(
            [f"<li>{factor}</li>" for factor in recommendation["main_factors_considered"][:4]]
        )
        if not factors_html:
            factors_html = "<li>Overall equipment profile</li>"

        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">1. WHY THIS RECOMMENDATION?</div>
                <p>{recommendation['reason']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">2. KEY FACTORS</div>
                <ul>
                    {factors_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">3. WHAT THIS MEANS</div>
                <p>{recommendation_meaning.get(recommendation['recommendation'], 'The equipment should be reviewed using the existing recommendation and current equipment information.')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="result-card">
                <div class="result-label">4. SUSTAINABILITY BENEFIT</div>
                <p>This recommendation supports responsible equipment lifecycle management by encouraging a practical, review-based approach to maintenance, reuse, or replacement.</p>
                <p>It aligns with SDG 12 by helping extend useful equipment life where appropriate and supporting a more responsible use of existing biomedical assets.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        assessment_entry = {
            "equipment_name": equipment_name,
            "equipment_category": equipment_category,
            "age": age_years,
            "current_condition": current_condition,
            "known_issue": known_issue,
            "last_maintenance": last_maintenance,
            "manufacturer_support": manufacturer_support,
            "usage_intensity": usage_intensity,
            "recommendation": recommendation["recommendation"],
            "reason": recommendation["reason"],
            "main_factors_considered": recommendation["main_factors_considered"],
            "ai_explanation": explanation,
            "logged_in_username": st.session_state["logged_in_user"],
            "user_role": st.session_state["logged_in_role"],
            "assessment_date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_assessment(assessment_entry)

        report_payload = {
            "equipment_name": equipment_name,
            "equipment_category": equipment_category,
            "age_years": age_years,
            "current_condition": current_condition,
            "known_issue": known_issue,
            "last_maintenance": last_maintenance,
            "manufacturer_support": manufacturer_support,
            "usage_intensity": usage_intensity,
            "recommendation": recommendation["recommendation"],
            "reason": recommendation["reason"],
            "main_factors_considered": recommendation["main_factors_considered"],
            "ai_explanation": explanation,
            "logged_in_username": st.session_state["logged_in_user"],
            "user_role": st.session_state["logged_in_role"],
            "assessment_date_time": assessment_entry["assessment_date_time"],
        }

        st.subheader("Assessment Report")
        report_text = generate_assessment_report(report_payload)
        st.download_button(
            label="Download Assessment Report",
            data=report_text,
            file_name="biomedical_equipment_assessment_report.txt",
            mime="text/plain",
        )

st.subheader("Assessment History")

history = load_assessment_history()
search_term = st.text_input("Search equipment name or recommendation")

if search_term:
    filtered_history = [
        item
        for item in history
        if search_term.lower() in str(item.get("equipment_name", "")).lower()
        or search_term.lower() in str(item.get("recommendation", "")).lower()
    ]
else:
    filtered_history = history

if filtered_history:
    history_df = []
    for item in filtered_history:
        history_df.append(
            {
                "Equipment Name": item.get("equipment_name", ""),
                "Category": item.get("equipment_category", ""),
                "Age": item.get("age", ""),
                "Condition": item.get("current_condition", ""),
                "Recommendation": item.get("recommendation", ""),
                "Username": item.get("logged_in_username", ""),
                "Role": item.get("user_role", ""),
                "Date & Time": item.get("assessment_date_time", ""),
            }
        )

    st.dataframe(history_df, use_container_width=True)
else:
    st.info("No assessment history available yet.")

if st.session_state.get("clear_history_message"):
    st.success(st.session_state.pop("clear_history_message"))

if st.button("Clear Assessment History"):
    st.session_state["clear_history_confirm_open"] = True

if st.session_state.get("clear_history_confirm_open"):
    st.warning("This will permanently remove all saved assessment history. Do you want to continue?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Yes, Clear History"):
            clear_assessment_history()
            st.session_state["clear_history_confirm_open"] = False
            st.session_state["clear_history_message"] = "Assessment history cleared successfully."
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.session_state["clear_history_confirm_open"] = False
            st.rerun()

st.subheader("Sustainability Dashboard")

history = load_assessment_history()
dashboard_stats = build_dashboard_stats(history)

st.markdown("### Assessment Statistics")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total assessments", dashboard_stats["total_assessments"])
col2.metric("Repair Assessments", dashboard_stats["repair_assessments"])
col3.metric("Refurbishment Considerations", dashboard_stats["refurbishment_considerations"])
col4.metric("Reuse Considerations", dashboard_stats["reuse_considerations"])
col5.metric("End-of-Life Reviews", dashboard_stats["end_of_life_reviews"])
col6.metric("Maintenance Assessments", dashboard_stats["maintenance_assessments"])

recommendation_categories = [
    "Continue Assessment",
    "Maintenance Assessment",
    "Repair Assessment",
    "Refurbishment Consideration",
    "Reuse Consideration",
    "End-of-Life Review",
]

chart_df = pd.DataFrame(
    {
        "Recommendation Type": recommendation_categories,
        "Number of Assessments": [
            dashboard_stats["distribution"].get(category, 0)
            for category in recommendation_categories
        ],
    }
)

chart = (
    alt.Chart(chart_df)
    .mark_bar(color="#2a9d8f")
    .encode(
        x=alt.X(
            "Recommendation Type:N",
            sort=recommendation_categories,
            title="Recommendation Type",
            axis=alt.Axis(
                labelAngle=0,
                labelFontSize=12,
                titleFontSize=13,
                labelLimit=200,
                labelOverlap="greedy",
            ),
        ),
        y=alt.Y(
            "Number of Assessments:Q",
            title="Number of Assessments",
            axis=alt.Axis(tickMinStep=1, titleFontSize=13, labelFontSize=11),
        ),
        tooltip=[
            alt.Tooltip("Recommendation Type:N", title="Recommendation Type"),
            alt.Tooltip("Number of Assessments:Q", title="Number of Assessments"),
        ],
    )
    .properties(
        title=alt.TitleParams(
            text="Equipment Life-Cycle Recommendations",
            fontSize=18,
            anchor="start",
            color="#0f4c81",
        ),
        width=900,
        height=280,
    )
    .configure_axis(
        labelColor="#1f2937",
        titleColor="#0f4c81",
        gridColor="#d8ebf7",
        domain=False,
    )
    .configure_view(stroke="transparent")
)

st.altair_chart(chart, use_container_width=False)
st.caption(
    "This chart shows how many equipment assessments resulted in each life-cycle recommendation."
)

st.markdown("### Dashboard Insight")

if dashboard_stats["total_assessments"] == 0:
    st.markdown(
        "<div class='section-card'><p>No assessment data is available yet.</p></div>",
        unsafe_allow_html=True,
    )
else:
    recommendation_counts = dashboard_stats["distribution"]
    max_count = max(recommendation_counts.values())
    most_common_recommendation = next(
        (
            category
            for category in recommendation_categories
            if recommendation_counts.get(category, 0) == max_count
        ),
        None,
    )

    if most_common_recommendation is None:
        st.markdown(
            "<div class='section-card'><p>No assessment data is available yet.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='section-card'><p>Most assessments currently result in <strong>{most_common_recommendation}</strong>, making it the most common life-cycle recommendation. Total assessments used for this insight: <strong>{dashboard_stats['total_assessments']}</strong>.</p></div>",
            unsafe_allow_html=True,
        )

st.markdown(
    "This dashboard shows the current distribution of recorded recommendations. "
    "Extending equipment life through appropriate maintenance, repair, refurbishment, or reuse can support "
    "responsible consumption and production by helping equipment remain useful for longer and reducing unnecessary early disposal."
)

st.info(
    "This is a basic starter project. Advanced AI, machine learning, databases, and API integrations will be added later."
)
