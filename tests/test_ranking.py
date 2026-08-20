from services.ranking_engine import rank_evaluations

def test_ranking():
    low = type("R", (), {
        "final_score": 70,
        "gate_status": "PASSED",
    })()
    high = type("R", (), {
        "final_score": 90,
        "gate_status": "PASSED",
    })()
    assert rank_evaluations([low, high])[0] is high
