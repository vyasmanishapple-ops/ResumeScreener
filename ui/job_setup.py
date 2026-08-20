import streamlit as st
from models.keywords import KeywordSignal


def _parse_lines(text, signal_type, default_weight):
    signals = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line and signal_type in {"POSITIVE", "NEGATIVE"}:
            keyword, weight = line.rsplit("|", 1)
            try:
                weight = float(weight.strip())
            except ValueError:
                weight = default_weight
        else:
            keyword, weight = line, default_weight
        signals.append(KeywordSignal(
            keyword=keyword.strip(),
            signal_type=signal_type,
            weight=weight,
        ))
    return signals


def keyword_editor():
    st.markdown("**Recruiter Signals**")
    st.caption("Positive/negative format: keyword | weight. One signal per line.")

    positive = st.text_area(
        "Positive Keywords",
        placeholder="AWS | 5\nEnterprise | 4\nLeadership | 3",
        height=80,
        key="positive_signals",
    )
    negative = st.text_area(
        "Negative Keywords",
        placeholder="Contract-only | -4\nNo client-facing experience | -5",
        height=80,
        key="negative_signals",
    )
    required = st.text_area(
        "Required Signals",
        placeholder="Security clearance\nWork authorization",
        height=80,
        key="required_signals",
    )
    disqualifying = st.text_area(
        "Disqualifying Signals",
        placeholder="Unable to work in required location",
        height=80,
        key="disqualifying_signals",
    )

    return (
        _parse_lines(positive, "POSITIVE", 1)
        + _parse_lines(negative, "NEGATIVE", -1)
        + _parse_lines(required, "REQUIRED", 0)
        + _parse_lines(disqualifying, "DISQUALIFYING", 0)
    )
