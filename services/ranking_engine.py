def rank_evaluations(results):
    return sorted(
        results,
        key=lambda item: (
            item.final_score,
            item.gate_status == "PASSED",
        ),
        reverse=True,
    )
