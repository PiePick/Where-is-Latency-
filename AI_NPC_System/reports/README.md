# CREDO Reports

This directory keeps only the current research-facing outputs.

## Current Paper Artifacts

- `credo_paper_draft_without_results.md`
  - Current paper draft without final user-study results.
- `latency_sensitivity_study_20260529/`
  - Latest quantitative latency simulation dataset and report.
  - Includes raw simulated turns, condition summaries, module summaries, assumptions, and the Korean explanation report.
  - `reliability_note_ko.md` clarifies that the 480,000 rows are empirical bootstrap simulation rows, not 480,000 real end-to-end VTuber executions.
- `survey_analysis_20260529/`
  - Latest anonymized survey analysis from the 27-response CSV.
  - Applies the corrected video order `case 3-1-5-2-4`, paired t-tests against SlowTrack Only, Cronbach alpha reliability checks, and English-exposure filtered summaries.
  - Includes a reference-guided results-method review and a paper-ready Results section draft.
- `survey_analysis_20260529_n31/`
  - Current latest survey analysis from the 31-response ZIP.
  - This supersedes the 27-response survey analysis for paper results.
  - Uses the same corrected video order `case 3-1-5-2-4` and the same reliability/test pipeline.

## Current Validation Artifacts

- `fasttrack_dataset_pool_validation_latest.md`
- `fasttrack_dataset_pool_validation_latest.json`
  - Latest FastTrack dataset pool validation summary.
- `runtime_readiness_latest.md`
- `runtime_readiness_latest.json`
  - Latest runtime readiness check output.

## Method Artifacts

- `intent_transition_matrix_from_swda.md`
- `intent_transition_matrix_from_swda.json`
  - SWDA-derived intent transition matrix used by the FastTrack routing method.
- `setfit_intent_evaluation.xlsx`
- `setfit_intent_evaluation_summary.json`
  - Intent classifier evaluation artifact.

## User Study Artifacts

- `user_study_response_template.csv`
  - Survey response template for the planned user study.

## Cleanup Policy

Intermediate filter reports, older latency simulations, obsolete voice/TTS reports, and exploratory benchmark folders are intentionally removed from this directory. Recreate them from scripts and logs only when needed.
