# Model Card: TARA Product Fit Scorer v1.0.0

## Model Details
- **Developer**: TARA AI Engineering
- **Model Date**: 2026-11-02
- **Model Type**: Explainable Logistic Regression with deterministic rule filters
- **Artifact**: `backend/app/scoring/model_weights.json` (Pure Python runtime, zero runtime ML dependencies)

## Intended Use
- Scoring customer and lead profiles against lending and banking products.
- Generates transparent, deterministic, plain-English explanations for credit recommendations.

## Training Data
- **Dataset**: 5,000 synthetic banking profiles with realistic Indian demographic distributions.
- **Features Used**:
  1. `monthly_income_norm`: Normalized income relative to ₹40,000 baseline
  2. `credit_score_norm`: Normalized credit score relative to 650 benchmark
  3. `age_fit`: Proximity to prime borrowing demographic (age 35 centered)
  4. `employment_salaried`: Binary indicator (1 for salaried, 0 for self-employed)
  5. `consent_flag`: Verification of applicant contact consent

## Evaluation Metrics (Held-out Test Split)
- **AUC-ROC**: **0.99** (synthetic benchmark)
- **Precision at Top 20%**: **1.0** (synthetic benchmark)

> **Important Notice on Metrics**: AUC-ROC and Precision-at-20% are computed exclusively on **SYNTHETIC labels** produced by a rule generator. They demonstrate the software pipeline and mathematical integration only, and are **NOT evidence of real-world underwriting accuracy or commercial credit performance**.

## Limitations & Ethical Considerations
- **Trained on synthetic data**: Model weights are calibrated exclusively on synthetic benchmarks. Must never be used for real statutory credit decisions without live bank calibration and fair lending review.
- **Pipeline demonstration only**: Does not claim or represent real-world predictive accuracy.
- **Rule Precedence**: Deterministic eligibility rules always override statistical fit scores.
