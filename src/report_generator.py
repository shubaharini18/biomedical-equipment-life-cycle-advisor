"""Generate a simple text assessment report for the biomedical equipment advisor."""


def _safe(value, fallback="Not provided"):
    """Return a safe display string for report fields."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() if value.strip() else fallback
    return str(value)


def generate_assessment_report(assessment_data):
    """Create a simple text assessment report using only Python built-ins."""
    recommendation = _safe(assessment_data.get("recommendation", "Not provided"))
    reason = _safe(assessment_data.get("reason", "Not provided"))
    factors = assessment_data.get("main_factors_considered") or []
    factors_text = ", ".join(factors) if factors else "Not provided"
    ai_explanation = _safe(assessment_data.get("ai_explanation", "Not provided"))

    lines = []
    lines.append("Biomedical Equipment Life-Cycle Advisor")
    lines.append("Project title: Biomedical Equipment Life-Cycle Advisor")
    lines.append("SDG 12: Responsible Consumption and Production")
    lines.append("")
    lines.append("Equipment name: " + _safe(assessment_data.get("equipment_name", "Not provided")))
    lines.append("Category: " + _safe(assessment_data.get("equipment_category", "Not provided")))
    lines.append("Age: " + _safe(assessment_data.get("age_years", "Not provided")))
    lines.append("Current condition: " + _safe(assessment_data.get("current_condition", "Not provided")))
    lines.append("Known issue/problem: " + _safe(assessment_data.get("known_issue", "Not provided")))
    lines.append("Last maintenance: " + _safe(assessment_data.get("last_maintenance", "Not provided")))
    lines.append("Manufacturer support: " + _safe(assessment_data.get("manufacturer_support", "Not provided")))
    lines.append("Usage intensity: " + _safe(assessment_data.get("usage_intensity", "Not provided")))
    lines.append("Sustainability recommendation: " + recommendation)
    lines.append("Reason: " + reason)
    lines.append("Main factors: " + factors_text)
    lines.append("AI explanation: " + ai_explanation)
    lines.append("Logged-in username: " + _safe(assessment_data.get("logged_in_username", "Not provided")))
    lines.append("User role: " + _safe(assessment_data.get("user_role", "Not provided")))
    lines.append("Date and time: " + _safe(assessment_data.get("assessment_date_time", "Not provided")))
    lines.append("")
    lines.append("Sustainability note: Appropriate maintenance, repair, refurbishment, or reuse can support responsible consumption and production by extending equipment life and reducing unnecessary early disposal.")
    lines.append(
        "Responsible-use disclaimer: This tool provides sustainability-oriented decision support only. It does not determine whether equipment is clinically safe for patient use. Final decisions must be made by qualified professionals."
    )

    return "\n".join(lines).encode("utf-8")
