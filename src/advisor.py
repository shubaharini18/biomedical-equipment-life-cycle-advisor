"""Basic advisory functions for the biomedical equipment life-cycle advisor."""


def get_lifecycle_recommendation(
    equipment_type,
    age_years,
    condition,
    maintenance_history,
    equipment_name=None,
    known_issue=None,
    repair_possible="No",
    refurbishment_possible="No",
    reuse_possible="No",
    last_maintenance=None,
    manufacturer_support=None,
    usage_intensity=None,
):
    """Return a simple, transparent, rule-based recommendation for equipment lifecycle planning."""

    factors = []
    if age_years >= 10:
        factors.append("equipment age")
    if condition in {"Fair", "Poor"}:
        factors.append("current condition")
    if maintenance_history == "Weak":
        factors.append("maintenance history")
    if known_issue:
        factors.append("known issue/problem")
    if last_maintenance in {"More than 1 year ago", "Never / Unknown"}:
        factors.append("maintenance timing")
    if manufacturer_support in {"Limited", "Not available"}:
        factors.append("manufacturer support")
    if usage_intensity == "High":
        factors.append("usage intensity")
    if repair_possible == "Yes":
        factors.append("repair feasibility")
    if refurbishment_possible == "Yes":
        factors.append("refurbishment feasibility")
    if reuse_possible == "Yes":
        factors.append("reuse feasibility")

    if not factors:
        factors = ["basic equipment profile"]

    if condition == "Poor" or age_years >= 12 or maintenance_history == "Weak":
        if repair_possible == "No" and refurbishment_possible == "No" and reuse_possible == "No":
            recommendation = "End-of-Life Review"
            reason = (
                f"For {equipment_type}, the equipment is aging or in poor condition, and there are no clear "
                "options for repair, refurbishment, or reuse after professional assessment."
            )
        elif refurbishment_possible == "Yes":
            recommendation = "Refurbishment Consideration"
            reason = (
                f"For {equipment_type}, refurbishment is the most suitable next step because the asset may still "
                "have value, but the current condition requires structured review."
            )
        elif repair_possible == "Yes":
            recommendation = "Repair Assessment"
            reason = (
                f"For {equipment_type}, repair should be assessed first because the equipment may be recoverable, "
                "but its poor condition and age increase risk and cost."
            )
        else:
            recommendation = "Reuse Consideration"
            reason = (
                f"For {equipment_type}, reuse may be worth considering if the equipment can be professionally assessed, "
                "but the current profile suggests caution."
            )

    elif condition == "Fair" or age_years >= 10:
        if repair_possible == "Yes":
            recommendation = "Repair Assessment"
            reason = (
                f"For {equipment_type}, repair is a reasonable option given the current condition, but the equipment "
                "should continue to be reviewed against cost, reliability, and safety requirements."
            )
        elif refurbishment_possible == "Yes":
            recommendation = "Refurbishment Consideration"
            reason = (
                f"For {equipment_type}, refurbishment should be considered because the device may benefit from a "
                "systematic restoration and requalification process."
            )
        elif reuse_possible == "Yes":
            recommendation = "Reuse Consideration"
            reason = (
                f"For {equipment_type}, reuse could be considered after professional assessment because the equipment "
                "may still have value, but the current condition requires review."
            )
        else:
            recommendation = "Maintenance Assessment"
            reason = (
                f"For {equipment_type}, preventive maintenance and monitored use are the most suitable immediate actions."
            )

    else:
        if last_maintenance in {"More than 1 year ago", "Never / Unknown"}:
            recommendation = "Maintenance Assessment"
            reason = (
                f"For {equipment_type}, the maintenance record suggests the equipment has not been serviced recently, "
                "so a maintenance assessment is the most suitable next step."
            )
        elif reuse_possible == "Yes":
            recommendation = "Reuse Consideration"
            reason = (
                f"For {equipment_type}, reuse may be appropriate after professional assessment, provided the equipment "
                "continues to meet operational requirements."
            )
        else:
            recommendation = "Continue Assessment"
            reason = (
                f"For {equipment_type}, the current profile supports continued assessment with routine monitoring and "
                "standard maintenance."
            )

    return {
        "recommendation": recommendation,
        "reason": reason,
        "main_factors_considered": factors,
        "decision_support_note": (
            "This is a decision-support recommendation only and is not a clinical safety decision."
        ),
        "equipment_name": equipment_name or "Unnamed equipment",
        "equipment_type": equipment_type,
        "condition": condition,
        "known_issue": known_issue or "Not provided",
    }
