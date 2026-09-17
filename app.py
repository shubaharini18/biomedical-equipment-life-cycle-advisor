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
            <div class=\"app-header-mark\" aria-hidden=\"true\">
                <span class=\"app-header-cross\"></span>
                <span class=\"app-header-pulse\"></span>
            </div>
            <div class=\"app-header-text\">
                <h1>AI-Based Biomedical Equipment Life-Cycle Advisor</h1>
                <p>AI-powered decision support for sustainable biomedical equipment management.</p>
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


def get_lifecycle_visual_state(recommendation_label, last_maintenance):
    """Return presentation-only lifecycle states from the existing assessment result."""

    stages = [
        "Procurement",
        "Installation",
        "Active Use",
        "Maintenance",
        "Lifecycle Review",
        "Recommended Action",
    ]

    if recommendation_label == "Continue Assessment":
        current_stage = "Active Use"
        summary = "The equipment remains in active use while routine monitoring continues."
    elif recommendation_label == "Maintenance Assessment":
        current_stage = "Maintenance"
        summary = "Maintenance is the current lifecycle focus based on the recorded service timing."
    else:
        current_stage = "Lifecycle Review"
        summary = "The equipment is currently under lifecycle review based on the existing assessment result."

    current_index = stages.index(current_stage)
    states = []
    for index, stage in enumerate(stages):
        if index < current_index:
            state = "completed"
        elif index == current_index:
            state = "current"
        else:
            state = "upcoming"
        states.append({"number": index + 1, "name": stage, "state": state})

    if current_stage == "Lifecycle Review" and last_maintenance == "Never / Unknown":
        summary = "The equipment is currently under lifecycle review because its maintenance record is unknown."

    return current_stage, summary, states


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
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .app-header {
            position: relative;
            background: linear-gradient(115deg, #0d3b66 0%, #0f5684 64%, #0a777c 100%);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            padding: 1.25rem 1.4rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 20px rgba(15, 76, 129, 0.13);
            overflow: hidden;
        }
        .app-header-content {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .app-header-mark {
            position: relative;
            flex: 0 0 64px;
            height: 64px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            background-color: rgba(255, 255, 255, 0.08);
            background-image: linear-gradient(rgba(255, 255, 255, 0.09) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.09) 1px, transparent 1px);
            background-size: 16px 16px;
        }
        .app-header-cross,
        .app-header-cross::after {
            position: absolute;
            content: \"\";
            background: #d9f7f2;
            border-radius: 2px;
        }
        .app-header-cross {
            width: 24px;
            height: 8px;
            top: 28px;
            left: 20px;
        }
        .app-header-cross::after {
            width: 8px;
            height: 24px;
            top: -8px;
            left: 8px;
        }
        .app-header-pulse {
            position: absolute;
            right: 8px;
            bottom: 9px;
            width: 18px;
            height: 2px;
            background: #8ee3d5;
            transform: rotate(-28deg);
            box-shadow: -8px 4px 0 -0.25px #8ee3d5, -13px 0 0 -0.25px #8ee3d5;
        }
        .app-header-text {
            flex: 1 1 auto;
            min-width: 0;
        }
        .app-header h1 {
            color: #ffffff !important;
            margin: 0;
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .app-header p {
            color: rgba(255, 255, 255, 0.9);
            margin-top: 0.5rem;
            margin-bottom: 0;
            font-size: 1rem;
        }
        .workspace-intro {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            background: #ffffff;
            border: 1px solid #d4e6f0;
            border-left: 4px solid #0e8c91;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin: 0.75rem 0 0.85rem;
            box-shadow: 0 4px 12px rgba(15, 76, 129, 0.05);
        }
        .workspace-intro h2 {
            margin: 0 0 0.18rem;
            color: #0d3b66;
            font-size: 1.35rem;
        }
        .workspace-intro p {
            margin: 0;
            color: #52677a;
            font-size: 0.92rem;
        }
        .workspace-intro-badge {
            flex: 0 0 auto;
            color: #0d6670;
            background: #e6f6f3;
            border: 1px solid #b9e5dd;
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid #d4e6f0;
            border-radius: 14px;
            padding: 1.1rem 1.2rem 0.85rem;
            box-shadow: 0 5px 16px rgba(15, 76, 129, 0.06);
        }
        div[data-testid="stForm"] h3 {
            color: #0d3b66;
            font-size: 1.05rem;
            letter-spacing: 0.02em;
            margin: 0.35rem 0 0.65rem;
            padding-bottom: 0.45rem;
            border-bottom: 1px solid #e2edf3;
        }
        .form-group-label {
            color: #0e6974;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.1em;
            margin: 0.7rem 0 0.1rem;
            text-transform: uppercase;
        }
        div[data-testid="stFormSubmitButton"] > button {
            width: 100%;
            min-height: 2.7rem;
            margin-top: 0.65rem;
            border-radius: 9px;
            background: #0d6670;
            border: 1px solid #0d6670;
            color: #ffffff;
            font-weight: 700;
            box-shadow: 0 5px 12px rgba(13, 102, 112, 0.18);
            transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
        }
        div[data-testid="stFormSubmitButton"] > button:hover {
            background: #0a525b;
            border-color: #0a525b;
            box-shadow: 0 7px 15px rgba(13, 102, 112, 0.24);
            transform: translateY(-1px);
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
            background: #ffffff;
            border: 1px solid #d4e6f0;
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 5px 16px rgba(15, 76, 129, 0.07);
            margin-bottom: 0.9rem;
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
        .result-card--primary {
            border-top: 4px solid #0e8c91;
            padding-top: 1rem;
        }
        .result-card--priority {
            border-left: 4px solid #0e8c91;
        }
        .result-card--action {
            background: #f2f8fc;
            border-left: 4px solid #0f5684;
        }
        .result-card--sustainability {
            background: #f3fbf7;
            border-color: #c5e8d5;
            border-left: 4px solid #2a9d68;
        }
        .result-card--ai {
            background: #f8fbfd;
            border-color: #d8e8f0;
        }
        .result-summary-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
            gap: 1rem;
            align-items: stretch;
        }
        .result-equipment-name {
            color: #0d3b66;
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 0.25rem;
        }
        .result-equipment-category {
            color: #52677a;
            font-size: 0.95rem;
        }
        .priority-panel {
            border-radius: 10px;
            padding: 0.8rem 0.9rem;
            border: 1px solid #c9e1eb;
            background: #f7fbfd;
        }
        .priority-panel--high {
            border-color: #efc3c0;
            background: #fff5f4;
        }
        .priority-panel--medium {
            border-color: #ecd39d;
            background: #fffaf0;
        }
        .priority-panel--low {
            border-color: #b9e1ca;
            background: #f3fbf6;
        }
        .priority-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.32rem 0.65rem;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .priority-badge--high {
            color: #a33a35;
            background: #fbe0de;
        }
        .priority-badge--medium {
            color: #956511;
            background: #f9e9bd;
        }
        .priority-badge--low {
            color: #217346;
            background: #dff3e6;
        }
        .priority-reason {
            color: #52677a;
            font-size: 0.85rem;
            line-height: 1.45;
            margin: 0.55rem 0 0;
        }
        .result-recommendation {
            color: #0d3b66;
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.25;
            margin: 0.1rem 0 0.85rem;
        }
        .result-action-label {
            color: #0e6974;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .result-factor-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.65rem;
        }
        .result-factor {
            background: #f8fbfd;
            border: 1px solid #deebf1;
            border-radius: 9px;
            padding: 0.65rem 0.75rem;
        }
        .result-factor .info-label {
            margin-bottom: 0.2rem;
            font-size: 0.68rem;
        }
        .result-factor-value {
            color: #263b4b;
            font-size: 0.9rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .result-card--sustainability p {
            color: #24543a;
        }
        .ai-section-note {
            color: #52677a;
            font-size: 0.88rem;
            margin: -0.15rem 0 0.75rem;
        }
        .lifecycle-card {
            background: #ffffff;
            border: 1px solid #d4e6f0;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 5px 16px rgba(15, 76, 129, 0.06);
            margin-bottom: 0.9rem;
        }
        .lifecycle-track {
            position: relative;
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.4rem;
            margin: 0.8rem 0 1rem;
        }
        .lifecycle-track::before {
            position: absolute;
            content: "";
            top: 16px;
            left: 7%;
            right: 7%;
            height: 2px;
            background: #dbe7ed;
        }
        .lifecycle-stage {
            position: relative;
            min-width: 0;
            text-align: center;
        }
        .lifecycle-marker {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            margin: 0 auto 0.45rem;
            border: 2px solid #d0dde4;
            border-radius: 50%;
            background: #f4f7f9;
            color: #7a8b96;
            font-size: 0.76rem;
            font-weight: 800;
        }
        .lifecycle-stage-name {
            color: #667985;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            line-height: 1.25;
            text-transform: uppercase;
        }
        .lifecycle-state {
            color: #87959d;
            font-size: 0.64rem;
            margin-top: 0.22rem;
            text-transform: uppercase;
        }
        .lifecycle-stage--completed .lifecycle-marker {
            border-color: #75b9bc;
            background: #e5f4f3;
            color: #0c6d73;
        }
        .lifecycle-stage--completed .lifecycle-stage-name {
            color: #2a6871;
        }
        .lifecycle-stage--current .lifecycle-marker {
            border-color: #0e8c91;
            background: #0e8c91;
            color: #ffffff;
            box-shadow: 0 0 0 5px #dff3f1;
        }
        .lifecycle-stage--current .lifecycle-stage-name,
        .lifecycle-stage--current .lifecycle-state {
            color: #0d5965;
            font-weight: 800;
        }
        .lifecycle-stage--upcoming {
            opacity: 0.7;
        }
        .lifecycle-summary-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 0.75fr);
            gap: 0.75rem;
        }
        .lifecycle-summary-item {
            background: #f7fbfd;
            border: 1px solid #deebf1;
            border-radius: 9px;
            padding: 0.7rem 0.8rem;
        }
        .lifecycle-summary-item--next {
            background: #f2f8fc;
            border-color: #cfe2ed;
        }
        .lifecycle-summary-value {
            color: #0d3b66;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.3;
        }
        .lifecycle-summary-text {
            color: #52677a;
            font-size: 0.86rem;
            line-height: 1.45;
            margin: 0.3rem 0 0;
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
        @media (max-width: 640px) {
            .app-header-mark {
                flex-basis: 50px;
                height: 50px;
            }
            .app-header h1 {
                font-size: 1.45rem;
            }
            .app-header p {
                font-size: 0.88rem;
            }
            .workspace-intro {
                align-items: flex-start;
                flex-direction: column;
            }
            div[data-testid="stForm"] {
                padding: 0.85rem 0.85rem 0.7rem;
            }
            .result-summary-grid,
            .result-factor-grid {
                grid-template-columns: 1fr;
            }
            .result-equipment-name {
                font-size: 1.4rem;
            }
            .lifecycle-track {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 0.9rem;
            }
            .lifecycle-track::before {
                display: none;
            }
            .lifecycle-summary-grid {
                grid-template-columns: 1fr;
            }
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

st.markdown(
    """
    <div class="workspace-intro">
        <div>
            <h2>Equipment Workspace</h2>
            <p>Enter the current equipment information to begin lifecycle assessment.</p>
        </div>
        <div class="workspace-intro-badge">Asset assessment</div>
    </div>
    """,
    unsafe_allow_html=True,
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

    st.markdown('<div class="form-group-label">Equipment profile</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="form-group-label">Current status</div>', unsafe_allow_html=True)

    known_issue = st.text_area("Known issue/problem")

    st.markdown('<div class="form-group-label">Lifecycle information</div>', unsafe_allow_html=True)

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
        priority_level = priority_result["priority"].split()[0].lower()
        current_lifecycle_stage, lifecycle_summary, lifecycle_states = get_lifecycle_visual_state(
            recommendation["recommendation"],
            last_maintenance,
        )
        lifecycle_stages_html = "".join(
            [
                f"<div class=\"lifecycle-stage lifecycle-stage--{stage['state']}\"><div class=\"lifecycle-marker\">{stage['number']}</div><div class=\"lifecycle-stage-name\">{stage['name']}</div><div class=\"lifecycle-state\">{stage['state']}</div></div>"
                for stage in lifecycle_states
            ]
        )

        st.markdown("### ASSESSMENT RESULT")
        st.markdown(
            f"""
            <div class="result-card result-card--primary">
                <div class="result-label">Decision support outcome</div>
                <div class="result-summary-grid">
                    <div>
                        <div class="info-label">Equipment assessed</div>
                        <div class="result-equipment-name">{equipment_name}</div>
                        <div class="result-equipment-category">{equipment_category}</div>
                    </div>
                    <div class="priority-panel priority-panel--{priority_level}">
                        <div class="info-label">Priority</div>
                        <div class="priority-badge priority-badge--{priority_level}">{priority_result['priority']}</div>
                        <p class="priority-reason">{priority_result['reason']}</p>
                    </div>
                </div>
                <div class="info-label" style="margin-top: 1rem;">Recommendation</div>
                <div class="result-title">{recommendation['recommendation']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### PRIORITY")
        st.markdown(
            f"""
            <div class="result-card result-card--priority priority-panel--{priority_level}">
                <span class="priority-badge priority-badge--{priority_level}">{priority_result['priority']}</span>
                <p class="priority-reason">{priority_result['reason']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### EQUIPMENT LIFE-CYCLE")
        st.markdown(
            f"""
            <div class="lifecycle-card">
                <div class="result-label">Lifecycle position</div>
                <div class="lifecycle-track">
                    {lifecycle_stages_html}
                </div>
                <div class="lifecycle-summary-grid">
                    <div class="lifecycle-summary-item">
                        <div class="info-label">Current lifecycle stage</div>
                        <div class="lifecycle-summary-value">{current_lifecycle_stage}</div>
                        <p class="lifecycle-summary-text">{lifecycle_summary}</p>
                    </div>
                    <div class="lifecycle-summary-item lifecycle-summary-item--next">
                        <div class="info-label">Next step</div>
                        <div class="lifecycle-summary-value">{recommendation['recommendation']}</div>
                        <p class="lifecycle-summary-text">{recommendation_action}</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### KEY FACTORS CONSIDERED")
        key_factors_html = "".join(
            [
                f"<div class='result-factor'><span class='info-label'>Equipment age</span><div class='result-factor-value'>{age_years} years</div></div>",
                f"<div class='result-factor'><span class='info-label'>Current condition</span><div class='result-factor-value'>{current_condition}</div></div>",
                f"<div class='result-factor'><span class='info-label'>Known issue / problem</span><div class='result-factor-value'>{known_issue}</div></div>",
                f"<div class='result-factor'><span class='info-label'>Maintenance status</span><div class='result-factor-value'>{maintenance_history}</div></div>",
                f"<div class='result-factor'><span class='info-label'>Last maintenance</span><div class='result-factor-value'>{last_maintenance}</div></div>",
                f"<div class='result-factor'><span class='info-label'>Manufacturer support</span><div class='result-factor-value'>{manufacturer_support}</div></div>",
                f"<div class='result-factor'><span class='info-label'>Usage intensity</span><div class='result-factor-value'>{usage_intensity}</div></div>",
            ]
        )
        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-factor-grid">
                    {key_factors_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### RECOMMENDED ACTION")
        st.markdown(
            f"""
            <div class="result-card result-card--action">
                <div class="result-action-label">Recommended action</div>
                <div class="result-recommendation">{recommendation['recommendation']}</div>
                <p>{recommendation_action}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### SUSTAINABILITY BENEFIT")
        st.markdown(
            """
            <div class="result-card result-card--sustainability">
                <div class="result-action-label">Sustainability benefit</div>
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
            <div class="result-card result-card--ai">
                <div class="result-label">1. WHY THIS RECOMMENDATION?</div>
                <p class="ai-section-note">A structured explanation based on the recorded equipment profile and existing recommendation.</p>
                <p>{recommendation['reason']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-card result-card--ai">
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
            <div class="result-card result-card--ai">
                <div class="result-label">3. WHAT THIS MEANS</div>
                <p>{recommendation_meaning.get(recommendation['recommendation'], 'The equipment should be reviewed using the existing recommendation and current equipment information.')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="result-card result-card--ai result-card--sustainability">
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
st.markdown("### ASSESSMENT OVERVIEW")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Assessments",
    dashboard_stats["total_assessments"],
)

col2.metric(
    "Maintenance Reviews",
    dashboard_stats["maintenance_assessments"],
)

col3.metric(
    "End-of-Life Reviews",
    dashboard_stats["end_of_life_reviews"],
)

lifecycle_reviews = (
    dashboard_stats["repair_assessments"]
    + dashboard_stats["refurbishment_considerations"]
    + dashboard_stats["reuse_considerations"]
)

col4.metric(
    "Lifecycle Reviews",
    lifecycle_reviews,
)

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
