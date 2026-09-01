# O1 — Payment Failure Economic Recovery Advisor

> **Razorpay Buildathon — Track 03: AI Revenue Recovery**

---

## Executive Summary & Problem Formulation

Payment failures cause significant recoverable revenue loss for online merchants. Traditional recovery systems rely on static decline-code rules or uniform immediate retries, leading to customer friction, unnecessary gateway costs, and suboptimal recovery rates.

**O1** is a post-payment-failure economic decision layer designed for Razorpay merchants. Given a failed payment episode and its context $X$, O1 evaluates bounded recovery interventions, estimates recovery probabilities $\hat{P}(\text{recovery} | X, a)$, calculates Expected Economic Value $EV(a | X)$ under hard safety constraints, and recommends the safety-constrained action that maximizes expected net economic recovery.

```
                  Payment Failure Context (X)
                              │
                              ▼
            Safety Gate (Hard Constraints Filter)
                              │
                              ▼
                Candidate Safe Actions A_safe(X)
                              │
                              ▼
       Recovery Probability Model P_hat(recovery | X, a)
                              │
                              ▼
       Expected Economic Value EV(a|X) = P_hat * V - C - D - F
                              │
                              ▼
          Policy Advisor (Argmax EV over A_safe)
                              │
                              ▼
       Recommended Recovery Action a* + Confidence Score
```

---

## Important Data Disclosure & Data Tier

> [!IMPORTANT]
> **TIER C — Public structural data + synthetic recovery environment**.
> - Production Razorpay transaction/customer data was **NOT** available for external ML training.
> - Transaction schemas and failure taxonomy codes are structurally inspired by public Razorpay API webhooks and developer documentation.
> - Historically logged actions, probabilistic recovery outcomes, recovery timestamps, and economic fee parameters are **synthetic modeled assumptions**.
> - Performance metrics represent simulated evidence within a controlled synthetic environment. No claims of actual Razorpay production recovery uplift are made.

---

## ML Model & Prediction Formulation

The machine learning estimator (`RecoveryPredictor`) models the conditional probability of payment recovery given the failure context $X$ and a candidate recovery action $a$:

$$P(\text{recovery} = 1 | X, \text{action})$$

Unlike standard binary classifiers that merely predict whether a payment will recover under its past attempt, **O1 evaluates candidate recovery actions**. At decision time, the model is queried across all allowable candidate actions $a \in A_{\text{safe}}(X)$ for the same context $X$.

### Input Features (24 Context Variables + Action)
- **Transaction**: `amount` ($V$), `currency`, `product_category`, `is_subscription`, `order_value_tier`
- **Payment Method & Issuer**: `payment_method`, `issuer_category`, `card_network`, `corridor`
- **Failure Taxonomy**: `failure_category`, `failure_code`, `error_source`, `error_step`
- **Customer History**: `customer_tenure_days`, `historical_success_rate`, `historical_failed_attempts`, `historical_retry_count`, `time_since_last_success_hours`, `retry_count_before_event`
- **Temporal & Merchant**: `hour`, `day_of_week`, `is_weekend`, `merchant_segment`, `merchant_category`
- **Action**: Candidate recovery action string $a$

---

## Expected Economic Value (EV) Formulation

The Policy Advisor selects the action maximizing net Expected Economic Value:

$$a^* = \arg\max_{a \in A_{\text{safe}}(X)} EV(a | X)$$

$$EV(a | X) = P(\text{recovery} | X, a) \cdot V - C(a) - D(a) - F(a)$$

Where:
- **$V$**: Transaction order value (`amount`).
- **$C(a)$**: Direct action execution cost (e.g. gateway fees, messaging cost).
- **$D(a)$**: Downside penalty (e.g. excessive retry penalties, misaligned prompt friction).
- **$F(a)$**: Customer friction cost proxy.

---

## Deterministic Safety Gate

The **Safety Gate** acts as an explicit pre-filter $A_{\text{safe}}(X)$ enforcing hard operational and compliance rules **before** policy evaluation:
- **Hard Declines & Fraud**: Fraud flags, stolen cards, blacklisted instruments, or velocity limits force $A_{\text{safe}}(X) = \{\text{do\_nothing}\}$.
- **Retry Cap Exceeded**: `retry_count_before_event` $\ge 3$ forces $A_{\text{safe}}(X) = \{\text{do\_nothing}\}$.
- **Stale Information Restrictions**: Expired cards require information update or method switch; passive retries are excluded.
- **Technical Failures**: Excludes useless information update prompts on network/gateway downtime.

The ML policy advisor can **never** override the Safety Gate.

---

## Non-Circular Synthetic Evaluation Design (Task 10)

To prevent circular evaluation (where a model simply re-discovers deterministic rules built into labels):
1. **Randomized Logging Policy**: Historical logs use an $\epsilon$-greedy policy ($\epsilon = 0.30$) over $A_{\text{safe}}(X)$, ensuring multiple actions appear across similar contexts (action overlap).
2. **Hidden Non-Linear Interactions**: Ground-truth probabilities $P_{\text{true}}(a|X)$ contain contextual interactions unknown to static baseline rules (e.g. PSU bank night batch windows 23:00–04:00, cross-border card friction, UPI peak-hour queue bottlenecks, order amount thresholds).
3. **Oracle Feature Isolation**: Ground-truth probabilities and oracle variables are stored separately in `*_oracle.csv` files and excluded from model inputs.

---

## Three Evaluation Pillars & Task 11 Results

Evaluation is strictly partitioned into three independent methodologies:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EVALUATION METHODOLOGY                          │
├──────────────────────────┬──────────────────────────┬──────────────────┤
│ A. Predictive Quality    │ B. Off-Policy IPS       │ C. Synthetic     │
│    (Observed Logged Set) │    (Propensity Match)   │    Oracle        │
└──────────────────────────┴──────────────────────────┴──────────────────┘
```

### Measured Results (Test Set: 15,000 Events)

#### Pillar A: Predictive Model Quality (Observed Actions)
- **Model Selected**: `HistGradientBoosting (Calibrated via Sigmoid 5-fold CV)`
- **Validation Brier Score**: `0.1516` | **Log Loss**: `0.4420` | **ROC AUC**: `0.8532`
- **Mean Calibration Error**: `0.0130`

#### Pillar B: Off-Policy Evaluation (Propensity-Weighted SNIPS)
- **Logged Policy Realized Mean EV**: **₹1,555.19** / event
- **Deterministic Baseline Policy SNIPS EV**: **₹1,546.59** / event (Coverage: 72.9%)
- **O1 ML Policy SNIPS EV**: **₹2,425.91** / event (Coverage: 38.5%, Effective Sample Size: 1,730.5)
- **Off-Policy Uplift over Baseline**: **+₹879.32 / event** (+56.8% economic gain)

#### Pillar C: Synthetic Oracle Benchmark (Ground-Truth Simulation)
- **Oracle Baseline Policy EV**: **₹1,668.04** / event
- **Oracle O1 ML Policy EV**: **₹2,349.72** / event
- **Oracle Best Policy EV**: **₹2,350.67** / event
- **Oracle Policy Regret**: **₹0.94 / event** (Near-zero regret relative to oracle optimum)

#### Safety Compliance
- **Safety Violation Count / Rate**: `0` (**0.00%** violation rate across 15,000 test events)

---

## Action Space & Recommended Policy Distribution

1. `retry_now`: Immediate retry (Policy Share: 21.8%)
2. `retry_later`: Delayed retry (Policy Share: 41.2%)
3. `switch_method`: Prompt method switch (Policy Share: 18.5%)
4. `update_information`: Prompt info update (Policy Share: 7.8%)
5. `do_nothing`: Abandon attempt (Policy Share: 10.7%)

---

## Reproducibility & Execution Commands

### 1. Environment Setup
```bash
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate Synthetic Dataset (100,000 Events, Seed 42)
```bash
python src/data/generate_synthetic.py --config configs/synthetic_config.yaml --events 100000 --outdir data/synthetic
```

### 3. Generate Data Manifest & Verify Checksums
```bash
python scripts/generate_data_manifest.py
```

### 4. Run Task 10 Sanity & Anti-Circularity Validation Suite
```bash
python -c "import pandas as pd; from src.data.validation import run_sanity_tests, print_validation_report; df_obs = pd.read_csv('data/synthetic/train.csv'); df_ora = pd.read_csv('data/synthetic/train_oracle.csv'); res = run_sanity_tests(df_obs, df_ora); print_validation_report(res)"
```

### 5. Train & Calibrate RecoveryPredictor Models
```bash
python scripts/train_recovery_model.py
```

### 6. Execute Policy Evaluation & Generate Report Figures
```bash
python scripts/evaluate_policy.py
```

### 7. Run Full Unit Test Suite
```bash
python -m unittest tests/test_generator.py
python -m unittest tests/test_anti_circularity.py
python -m unittest tests/test_task11_policy.py
```

---

## Repository Structure

```text
Razorpay/
├── .gitignore
├── CONTRIBUTING.md
├── DATASET_CARD.md
├── DATA_ACCESS.docx
├── README.md
├── SYNTHETIC_GENERATION.md
├── TASK_11_RESULTS.md
├── Task_9_O1_System_Specification.docx
├── requirements.txt
├── configs/
│   └── synthetic_config.yaml
├── data/
│   └── synthetic/
│       └── checksums.json
├── models/
│   └── recovery_predictor.joblib
├── reports/
│   ├── task11_model_results.json
│   ├── task11_policy_evaluation.json
│   └── figures/
│       ├── action_distribution.png
│       ├── calibration_curve.png
│       ├── ev_comparison.png
│       └── prob_distribution.png
├── scripts/
│   ├── evaluate_policy.py
│   ├── generate_data_manifest.py
│   └── train_recovery_model.py
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── economics.py
│   │   ├── failure_taxonomy.py
│   │   ├── generate_synthetic.py
│   │   ├── ground_truth.py
│   │   ├── logging_policy.py
│   │   ├── safety.py
│   │   └── validation.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── preprocessing.py
│   │   └── recovery_predictor.py
│   └── policy/
│       ├── __init__.py
│       ├── advisor.py
│       ├── baseline.py
│       └── evaluation.py
└── tests/
    ├── test_anti_circularity.py
    ├── test_generator.py
    └── test_task11_policy.py
```

---

## Project Limitations

1. **No Production Razorpay Data**: Experiments use Tier C synthetic environment data.
2. **Modeled Economics**: Cost parameters $C(a)$, $D(a)$, $F(a)$ represent domain assumptions, not Razorpay fee contracts.
3. **Off-Policy Coverage**: IPS evaluations rely on match subset coverage ($38.5\%$) within the synthetic randomized logging environment ($\epsilon = 0.30$).
4. **Synthetic Benchmark**: Oracle benchmarks measure regret against synthetic equations, not real-world customer counterfactuals.
5. **Non-Causal Bounds**: Results demonstrate machine learning optimization capability within controlled environments, not causal real-world customer behavior.
