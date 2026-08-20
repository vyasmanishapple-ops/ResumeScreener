from datetime import datetime
from models.evaluation import EvaluationResult
from services.evidence_matcher import match_requirement
from services.keyword_engine import analyze_keywords
from services.scoring_engine import calculate_score
from services.validation_engine import validate

def evaluate_candidate(jd, candidate, resume_text, signals, model):
    matches = [match_requirement(r, candidate, model) for r in jd.requirements]
    keywords = analyze_keywords(resume_text, signals, model)
    score = calculate_score(jd.requirements, matches, keywords)
    errors = validate(jd.requirements, matches, score)
    if errors:
        raise ValueError("; ".join(errors))

    return EvaluationResult(
        candidate_name=candidate.candidate_name,
        candidate_email=candidate.email,
        job_title=jd.job_title,
        base_score=score["base_score"],
        keyword_adjustment=score["keyword_adjustment"],
        final_score=score["final_score"],
        gate_status=score["gate_status"],
        recommendation=score["recommendation"],
        requirement_matches=matches,
        keyword_detections=keywords,
        contradictions=[
            m.explanation for m in matches if m.status == "CONTRADICTED"
        ],
        strengths=[
            f"{m.requirement_name}: {m.explanation}"
            for m in matches if m.status == "EXPLICIT_MATCH"
        ],
        gaps=[
            m.requirement_name for m in matches
            if m.status in {"NO_EVIDENCE", "CONTRADICTED"}
        ],
        model_name=model,
        prompt_version="1.0",
        scoring_version="1.0",
        created_at=datetime.utcnow(),
    )
