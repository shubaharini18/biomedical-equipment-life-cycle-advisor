"""Simple dashboard helpers for assessment history statistics."""

from collections import Counter


def build_dashboard_stats(history):
    """Build simple, transparent recommendation statistics from stored assessments."""
    total_assessments = len(history)

    recommendation_counts = Counter(
        item.get("recommendation", "Unknown") for item in history if item.get("recommendation")
    )

    return {
        "total_assessments": total_assessments,
        "repair_assessments": recommendation_counts.get("Repair Assessment", 0),
        "refurbishment_considerations": recommendation_counts.get("Refurbishment Consideration", 0),
        "reuse_considerations": recommendation_counts.get("Reuse Consideration", 0),
        "end_of_life_reviews": recommendation_counts.get("End-of-Life Review", 0),
        "maintenance_assessments": recommendation_counts.get("Maintenance Assessment", 0),
        "distribution": recommendation_counts,
    }
