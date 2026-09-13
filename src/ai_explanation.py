"""Simple AI-style explanation generator for sustainability-focused equipment recommendations."""


def generate_ai_explanation(equipment_details, recommendation):
    """
    Create a short, structured explanation for the current recommendation.

    This stays lightweight and uses the existing recommendation plus the current
    equipment details as the basis for the explanation.
    """

    equipment_name = equipment_details.get("equipment_name", "Unnamed equipment")
    equipment_type = equipment_details.get("equipment_type", recommendation.get("equipment_type", "equipment"))
    age_years = equipment_details.get("age_years", 0)
    condition = equipment_details.get("condition", "Unknown")
    known_issue = equipment_details.get("known_issue", "Not provided")

    repair_possible = equipment_details.get("repair_possible", "No")
    refurbishment_possible = equipment_details.get("refurbishment_possible", "No")
    reuse_possible = equipment_details.get("reuse_possible", "No")

    recommendation_label = recommendation.get("recommendation", "Recommendation")
    reason = recommendation.get("reason", "No reason provided.")
    factors = recommendation.get("main_factors_considered", [])

    factor_text = factors[:3]
    if not factor_text:
        factor_text = ["overall equipment profile"]

    bullets = "\n".join(f"- {factor}" for factor in factor_text)

    explanation = (
        f"1. Why this recommendation?\n"
        f"{reason[:240]}\n\n"
        f"2. Key factors\n"
        f"{bullets}\n\n"
        f"3. Sustainability benefit\n"
        f"This recommendation supports practical sustainability by helping extend useful equipment life where appropriate. "
        f"It is intended as decision support only and is not a clinical safety decision."
    )

    return explanation
