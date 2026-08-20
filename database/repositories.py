import json
from datetime import datetime
from database.database import SessionLocal
from database.models import Candidate, Job, Evaluation

def normalize_email(email):
    return email.strip().lower()

def next_evaluation_number(session):
    count = session.query(Evaluation).count() + 1
    return f"EVAL-{datetime.now().year}-{count:06d}"

def save_evaluation(result, jd_text):
    with SessionLocal() as session:
        email = normalize_email(result.candidate_email)
        candidate = session.query(Candidate).filter(
            Candidate.email == email
        ).first()

        if candidate is None:
            candidate = Candidate(
                name=result.candidate_name,
                email=email,
            )
            session.add(candidate)
            session.flush()

        job = Job(
            title=result.job_title,
            description=jd_text,
        )
        session.add(job)
        session.flush()

        result.evaluation_number = next_evaluation_number(session)

        row = Evaluation(
            evaluation_number=result.evaluation_number,
            candidate_id=candidate.id,
            job_id=job.id,
            candidate_name=result.candidate_name,
            candidate_email=email,
            job_title=result.job_title,
            base_score=result.base_score,
            keyword_adjustment=result.keyword_adjustment,
            final_score=result.final_score,
            gate_status=result.gate_status,
            recommendation=result.recommendation,
            payload_json=result.model_dump_json(),
            model_name=result.model_name,
            prompt_version=result.prompt_version,
            scoring_version=result.scoring_version,
            created_at=result.created_at,
        )
        session.add(row)
        session.commit()
        return result

def history_by_email(email):
    with SessionLocal() as session:
        return session.query(Evaluation).filter(
            Evaluation.candidate_email == normalize_email(email)
        ).order_by(Evaluation.created_at.desc()).all()

def get_evaluation(number):
    with SessionLocal() as session:
        row = session.query(Evaluation).filter(
            Evaluation.evaluation_number == number
        ).first()
        return json.loads(row.payload_json) if row else None

def update_recruiter_decision(number, decision, notes):
    with SessionLocal() as session:
        row = session.query(Evaluation).filter(
            Evaluation.evaluation_number == number
        ).first()
        if not row:
            return False
        row.recruiter_decision = decision
        row.recruiter_notes = notes
        payload = json.loads(row.payload_json)
        payload["recruiter_decision"] = decision
        payload["recruiter_notes"] = notes
        row.payload_json = json.dumps(payload)
        session.commit()
        return True

def save_jd_version(analysis, jd_text, ai_original):
    """Persist a recruiter-approved JD model independently of candidate evaluations."""
    from database.models import JobDescriptionVersion
    with SessionLocal() as session:
        row = JobDescriptionVersion(
            job_title=analysis.job_title,
            raw_jd_text=jd_text,
            ai_generated_model_json=ai_original.model_dump_json(),
            approved_model_json=analysis.model_dump_json(),
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_jd_version(version_id):
    from database.models import JobDescriptionVersion
    with SessionLocal() as session:
        row = session.query(JobDescriptionVersion).filter(
            JobDescriptionVersion.id == int(version_id)
        ).first()
        return row
