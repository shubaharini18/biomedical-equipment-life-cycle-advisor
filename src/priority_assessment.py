"""Simple rule-based equipment priority assessment helper."""


def assess_equipment_priority(age_years, condition, known_issue):
    """Return a simple priority level and short reason based on equipment inputs."""

    issue_present = bool((known_issue or "").strip())

    if condition == "Poor" or age_years >= 10 or (issue_present and condition == "Poor"):
        return {
            "priority": "High Priority",
            "reason": "The equipment is older or in poor condition, and the reported issue suggests timely review is needed.",
        }

    if condition == "Fair" or age_years >= 5 or issue_present:
        return {
            "priority": "Medium Priority",
            "reason": "The equipment has some age or condition concerns, so it should be reviewed soon.",
        }

    return {
        "priority": "Low Priority",
        "reason": "The equipment is currently in acceptable condition and does not show an urgent need for action.",
    }
