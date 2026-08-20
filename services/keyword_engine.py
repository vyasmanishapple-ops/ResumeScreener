from llm.client import LocalLLM
from llm.prompts import KEYWORD_SYSTEM
from llm.schemas import KeywordAnalysisSchema
from models.keywords import KeywordDetection

def analyze_keywords(candidate_text, signals, model=None):
    active = [s for s in signals if s.enabled]
    if not active:
        return []

    payload = "\n".join(str(s.model_dump()) for s in active)
    result = LocalLLM(model).structured(
        KeywordAnalysisSchema,
        KEYWORD_SYSTEM,
        "RECRUITER SIGNALS:\n" + payload + "\n\nRESUME:\n" + candidate_text,
    )

    output = []
    for signal in active:
        found = next(
            (x for x in result.detections
             if x.keyword.lower() == signal.keyword.lower()),
            None,
        )
        detected = bool(found and found.detected and found.relevant)
        adjustment = signal.weight if (
            detected and signal.signal_type in {"POSITIVE", "NEGATIVE"}
        ) else 0
        output.append(KeywordDetection(
            keyword=signal.keyword,
            signal_type=signal.signal_type,
            configured_weight=signal.weight,
            detected=detected,
            context=found.context if found else "",
            relevant=detected,
            applied_adjustment=adjustment,
        ))
    return output
