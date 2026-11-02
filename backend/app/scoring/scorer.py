"""
Pure-Python runtime scoring engine for product fit and eligibility checking.
Reads precomputed weights artifact; requires zero runtime machine-learning dependencies.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

WEIGHTS_PATH = Path(__file__).parent / "model_weights.json"

BAND_HIGH_THRESHOLD = 70
BAND_MEDIUM_THRESHOLD = 40


def load_model_weights() -> Dict[str, Any]:
    """Load pre-trained model weights artifact from disk."""
    if not WEIGHTS_PATH.exists():
        return {
            "model_version": "1.0.0",
            "coefficients": [0.9715, 0.5200, 0.4029, 0.5829, 0.6314],
            "intercept": 0.5976,
        }
    with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_WEIGHTS = load_model_weights()


def evaluate_eligibility(
    record: Dict[str, Any], product: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Evaluate deterministic lending criteria against product rules."""
    rules = product.get("eligibility_rules", {})
    failed: List[str] = []

    income = float(record.get("monthly_income_inr", 0))
    min_income = float(rules.get("min_income", 0))
    if income < min_income:
        failed.append(f"Monthly income ₹{int(income):,} is below required ₹{int(min_income):,}")

    age = int(record.get("age", 0))
    min_age = int(rules.get("min_age", 18))
    max_age = int(rules.get("max_age", 70))
    if age < min_age:
        failed.append(f"Age {age} is below minimum requirement of {min_age}")
    elif age > max_age:
        failed.append(f"Age {age} exceeds maximum allowed of {max_age}")

    credit_score = int(record.get("credit_score", 0))
    min_credit = int(rules.get("min_credit_score", 300))
    if credit_score < min_credit:
        failed.append(f"Credit score {credit_score} is below benchmark {min_credit}")

    emp_type = str(record.get("employment_type", "")).strip().lower()
    allowed_emp = [str(e).strip().lower() for e in rules.get("employment_types", [])]
    if allowed_emp and emp_type not in allowed_emp:
        failed.append(f"Employment type '{emp_type}' not in allowed list ({', '.join(allowed_emp)})")

    return (len(failed) == 0, failed)


def compute_fit_score(
    record: Dict[str, Any], product: Dict[str, Any]
) -> Tuple[int, str, List[str]]:
    """
    Calculate fit score (0-100), band assignment, and top 3 plain-English explanations.

    Returns (fit_score, band, explanations).
    """
    coefs = _WEIGHTS.get("coefficients", [0.97, 0.52, 0.40, 0.58, 0.63])
    intercept = _WEIGHTS.get("intercept", 0.60)

    income = float(record.get("monthly_income_inr", 30000))
    score = int(record.get("credit_score", 650))
    age = int(record.get("age", 30))
    salaried = 1.0 if str(record.get("employment_type", "")).lower() == "salaried" else 0.0
    consent = 1.0 if record.get("consent") else 0.0

    # Centered normalized features
    x_inc = (income - 40000.0) / 40000.0
    x_score = (score - 650.0) / 100.0
    x_age = (1.0 - abs(age - 35) / 25.0) - 0.5
    x_sal = salaried - 0.5
    x_con = consent - 0.5

    features = [x_inc, x_score, x_age, x_sal, x_con]
    z = intercept + sum(w * xi for w, xi in zip(coefs, features))
    prob = 1.0 / (1.0 + math.exp(-max(min(z, 20.0), -20.0)))
    fit_score = int(round(prob * 100))

    if fit_score >= BAND_HIGH_THRESHOLD:
        band = "High"
    elif fit_score >= BAND_MEDIUM_THRESHOLD:
        band = "Medium"
    else:
        band = "Low"

    # Top contributing features with direction and magnitude
    contributions = [
        (
            coefs[0] * x_inc,
            f"Monthly income ₹{int(income):,} supports credit capacity"
            if coefs[0] * x_inc > 0.5
            else f"Monthly income ₹{int(income):,} is below average benchmark",
        ),
        (
            coefs[1] * x_score,
            f"Credit score {score} demonstrates strong repayment history"
            if score >= 700
            else f"Credit score {score} limits borrowing tier",
        ),
        (
            coefs[2] * x_age,
            f"Age {age} is in prime repayment demographic"
            if 25 <= age <= 50
            else f"Age {age} falls outside core credit demographic",
        ),
        (
            coefs[3] * x_sal,
            "Salaried employment provides stable cash flow"
            if salaried == 1.0
            else "Self-employed profile requires additional verification",
        ),
        (
            coefs[4] * x_con,
            "Documented outreach consent confirmed"
            if consent == 1.0
            else "Missing contact consent limits reachability",
        ),
    ]

    contributions.sort(key=lambda item: abs(item[0]), reverse=True)
    top_explanations = [item[1] for item in contributions[:3]]

    return fit_score, band, top_explanations
