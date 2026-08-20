# Current library fixes

## JD parser
- Responsibility source-bullet granularity validation now detects both:
  - multiple extracted rows mapped to the same JD bullet
  - one extracted source spanning multiple JD bullets
- Granularity findings are diagnostic: JD-supported requirements are retained and surfaced as `[REVIEW]` notes instead of being silently removed.
- Existing metadata-only location/work-arrangement protection remains intact.
- Existing HARD safety for RESPONSIBILITY and SUCCESS_MEASURE remains intact.

## JD review UI
- Refresh Distribution accepts DataFrame and list-based editor results.
- Refresh recalculates the current recruiter-edited weights without an LLM call.
- Weight distribution includes every category present in the JD model, including zero-weight categories in the text breakdown.
- Possible Duplicates remains grouped and displays `req_id [CATEGORY]: requirement`.

## Validation
- All Python files compile successfully in this packaged copy.
- Full pytest execution was not available in this environment because the uploaded environment does not include the project's `instructor` and `streamlit` packages. Run the project's `.venv` pytest locally.
