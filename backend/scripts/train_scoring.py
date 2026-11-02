"""
Offline training script for TARA Product Fit Scorer.
Generates synthetic customer-product interactions with realistic risk dynamics,
evaluates on a held-out split (AUC, Precision@20%), and commits model_weights.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random

OUT_PATH = Path(__file__).parent.parent / "app" / "scoring" / "model_weights.json"
DOCS_PATH = Path(__file__).parent.parent.parent / "docs" / "MODEL_CARD.md"

random.seed(42)

FEATURE_NAMES = [
    "monthly_income_norm",
    "credit_score_norm",
    "age_fit",
    "employment_salaried",
    "consent_flag",
]


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(z, 20.0), -20.0)))


def generate_synthetic_dataset(n: int = 5000):
    dataset = []
    for _ in range(n):
        income = random.uniform(15000, 200000)
        score = random.randint(350, 850)
        age = random.randint(21, 65)
        salaried = 1.0 if random.random() < 0.7 else 0.0
        consent = 1.0 if random.random() < 0.9 else 0.0

        # Centered normalization
        x_inc = (income - 40000.0) / 40000.0
        x_score = (score - 650.0) / 100.0
        x_age = (1.0 - abs(age - 35) / 25.0) - 0.5
        x_sal = salaried - 0.5
        x_con = consent - 0.5

        # True latent score
        latent = 1.2 * x_score + 1.0 * x_inc + 0.6 * x_sal + 0.5 * x_age + 0.8 * x_con - 0.4
        prob = sigmoid(latent + random.gauss(0, 0.35))
        label = 1 if prob >= 0.5 else 0

        dataset.append(([x_inc, x_score, x_age, x_sal, x_con], label))
    return dataset


def train_logistic_regression(dataset, epochs=200, lr=0.1):
    split = int(len(dataset) * 0.8)
    train_data = dataset[:split]
    test_data = dataset[split:]

    weights = [0.0] * len(FEATURE_NAMES)
    bias = 0.0

    for _ in range(epochs):
        for x, y in train_data:
            z = bias + sum(w * xi for w, xi in zip(weights, x))
            p = sigmoid(z)
            err = y - p
            bias += lr * err / len(train_data)
            for j in range(len(weights)):
                weights[j] += lr * err * x[j] / len(train_data)

    scores_labels = []
    for x, y in test_data:
        z = bias + sum(w * xi for w, xi in zip(weights, x))
        scores_labels.append((sigmoid(z), y))

    scores_labels.sort(key=lambda t: t[0], reverse=True)
    top_20_count = max(1, int(len(scores_labels) * 0.2))
    top_20 = scores_labels[:top_20_count]
    precision_at_20 = sum(y for _, y in top_20) / top_20_count

    positives = [s for s, y in scores_labels if y == 1]
    negatives = [s for s, y in scores_labels if y == 0]
    concordant = sum(1 for p in positives for n in negatives if p > n)
    ties = sum(0.5 for p in positives for n in negatives if p == n)
    auc = (concordant + ties) / (len(positives) * len(negatives)) if positives and negatives else 0.5

    return weights, bias, round(auc, 3), round(precision_at_20, 3)


def main():
    data = generate_synthetic_dataset(5000)
    weights, bias, auc, prec_20 = train_logistic_regression(data)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model_version": "1.0.0",
        "algorithm": "LogisticRegression",
        "trained_on": "Synthetic Indian banking outreach profiles (5,000 samples)",
        "features": FEATURE_NAMES,
        "coefficients": [round(w, 4) for w in weights],
        "intercept": round(bias, 4),
        "metrics": {"auc": auc, "precision_at_top_20": prec_20},
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)

    model_card = f"""# Model Card: TARA Product Fit Scorer v1.0.0

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
- **AUC-ROC**: **{auc}**
- **Precision at Top 20%**: **{prec_20}**

## Limitations & Ethical Considerations
- **Trained on synthetic data**: Model weights are calibrated exclusively on synthetic benchmarks. Must never be used for real statutory credit decisions without live bank calibration and fair lending review.
- **Rule Precedence**: Deterministic eligibility rules always override statistical fit scores.
"""
    with open(DOCS_PATH, "w", encoding="utf-8") as f:
        f.write(model_card)
    print(f"Trained: AUC={auc}, Prec@20={prec_20}, bias={bias}")


if __name__ == "__main__":
    main()
