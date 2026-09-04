# SYNTHETIC DATASET GENERATION ARCHITECTURE & REPRODUCIBILITY GUIDE

## Overview
This document details the data-generating process, mathematical formulations, safety constraints, economic parameters, and anti-circularity safeguards built into the synthetic dataset for **Payment Recovery** (Built for Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery).

---

## Data Generation Pipeline

The generation pipeline processes failure events chronologically through 5 sequential layers:

```
[1. Context Generation (X)] 
           │
           ▼
[2. Safety Gate Layer (A_safe(X))]
           │
           ▼
[3. Historical Logging Policy (P_logged(a|X))] ──► Logs: logged_action & propensity
           │
           ▼
[4. Hidden Ground-Truth Engine (P_true(a|X))] ──► Samples: Bernoulli recovery outcome
           │
           ▼
[5. Economic Valuation Engine (EV(a|X))] ──► Computes: EV for Logged, Baseline, Oracle
```

---

## 1. Context Generation ($X$)
Context vector $X$ represents all observable features at the moment of payment failure:
- **Transaction**: Amount $V \sim \text{LogNormal}(\mu=7.5, \sigma=1.2)$, Currency, Order Value Tier.
- **Payment Method & Issuer**: Payment Method, Issuer Category (`psu_bank`, `private_bank`, `foreign_bank`, `neobank`), Card Network, Corridor (`domestic_in`, `cross_border_in_*`).
- **Failure Taxonomy**: Category assigned via realistic distribution probabilities across 13 taxonomy types.
- **Customer History**: Historical authorization rate $\sim \text{Beta}(\alpha=7, \beta=3)$, Tenure, Retry Count Before Event.
- **Temporal**: Hour of day, Day of week, Weekend flag.

---

## 2. Safety Gate Layer ($A_{\text{safe}}(X)$)
Deterministic safety layer evaluating $X$ before any action assignment or policy evaluation.

### Safety Rules:
1. **Hard Declines / Fraud / Blocked Accounts**:
   $$\text{failure\_category} \in \{\text{hard\_decline}, \text{blocked\_instrument}, \text{velocity\_limit}\} \implies A_{\text{safe}}(X) = \{\text{do\_nothing}\}$$
2. **Retry Cap Exceeded**:
   $$\text{retry\_count\_before\_event} \ge 3 \implies A_{\text{safe}}(X) = \{\text{do\_nothing}\}$$
3. **Stale Information Restrictions**:
   $$\text{failure\_category} \in \{\text{expired\_card}, \text{invalid\_information}\} \implies A_{\text{safe}}(X) \cap \{\text{retry\_now}, \text{retry\_later}\} = \emptyset$$
4. **Technical Failure Restrictions**:
   $$\text{failure\_category} \in \{\text{soft\_decline}, \text{upi\_timeout}, \dots\} \implies A_{\text{safe}}(X) \setminus \{\text{update\_information}\}$$

---

## 3. Historical Logging Policy ($P_{\text{logged}}(a|X)$)
To avoid circular evaluation, historical logged actions are generated using an **$\epsilon$-greedy mixture logging policy** ($\epsilon = 0.30$):
- **70% Probability**: Follows standard historical merchant heuristic.
- **30% Probability**: Uniformly distributed over all actions in $A_{\text{safe}}(X)$.

$$P_{\text{logged}}(a | X) = (1 - \epsilon) \cdot \mathbb{I}(a = a_{\text{heuristic}}) + \frac{\epsilon}{|A_{\text{safe}}(X)|}$$

This guarantees **action positivity and overlap** across feature contexts:
- Multiple feasible actions appear for similar contexts.
- The optimal action is NOT deterministically assigned in the dataset.

---

## 4. Hidden Ground-Truth Recovery Engine ($P(\text{recovery} | X, a)$)
The true recovery probability is calculated via a hidden non-linear logit function:

$$\text{logit}(P(\text{recovery} | X, a)) = \beta_0 + \gamma(a) + \delta(\text{cat}) + \text{Interactions}(X, a) + \text{CustomerSignal}$$

$$P(\text{recovery} | X, a) = \sigma(\text{logit})$$

### Key Hidden Contextual Interactions:
1. **PSU Bank Night Maintenance Window**: During 23:00–04:00, PSU banks undergo batch processing. `retry_now` logit drops by $-2.5$ ($P_{\text{rec}} < 5\%$), whereas `retry_later` (scheduled next morning) or `switch_method` gains $+1.5$ ($P_{\text{rec}} \approx 65\%$).
2. **Cross-Border Corridor Friction**: International card payments face 3DS/risk holds. `switch_method` or local auth prompt gains $+1.0$ logit vs `retry_now`.
3. **UPI Peak-Hour Queue Bottleneck**: During evening peak hours (18:00–21:00), NPCI queues overflow. Instant retries cause cascade timeouts ($-1.8$ logit); `retry_later` or `switch_method` gains $+1.4$ logit.
4. **Order Amount Threshold**: High value orders ($> \text{₹}10,000$) require explicit customer action (`switch_method`, `update_information`) to recover; passive retries decay rapidly.
5. **Retry Count Decay**: Each prior attempt decays recovery logit by $-0.4 \cdot \text{retry\_count}$.

### Probabilistic Sampling:
Outcomes are sampled stochastically:
$$\text{recovered} \sim \text{Bernoulli}(P(\text{recovery} | X, a_{\text{logged}}))$$
If recovered, recovery timestamp is generated within a 72-hour attribution window using action-specific exponential time distributions.

---

## 5. Economic Valuation Model ($EV(a | X)$)
Expected economic value is defined as:

$$EV(a | X) = P(\text{recovery} | X, a) \cdot V - C(a) - D(a) - F(a)$$

Where:
- $V$: Order amount.
- $C(a)$: Direct action cost (`retry_now`: ₹2, `retry_later`: ₹3, `switch_method`: ₹5, `update_information`: ₹7, `do_nothing`: ₹0).
- $D(a)$: Downside penalty (₹15 penalty if retrying when retry count $\ge 2$; ₹5 penalty for misaligned information prompts).
- $F(a)$: Customer friction cost (`retry_now`: ₹1, `retry_later`: ₹2, `switch_method`: ₹10, `update_information`: ₹20, `do_nothing`: ₹0).

---

## 6. Anti-Circularity Safeguards Summary

> [!NOTE]
> **HISTORICAL / PRE-TASK 16B VALIDATION METRICS**: The verification metrics in the table below record initial dataset sanity checks from generation (Task 10/11). Current authoritative evaluation metrics are in `reports/task11_policy_evaluation.json` and `reports/task12_robustness.json`.

| Question | Safeguard Mechanism | Verification Status |
| :--- | :--- | :--- |
| **1. Who chooses historical action?** | $\epsilon$-greedy historical policy ($\epsilon = 0.30$) | **PASSED** (soft_decline has 4 distinct logged actions) |
| **2. Does logging policy know optimal action?** | No, uses standard heuristic + uniform exploration | **PASSED** (Max action share = 74.31%) |
| **3. Does baseline know hidden recovery function?** | No, baseline uses static rules | **PASSED** (Oracle EV ₹2,352.43 > Baseline EV ₹1,662.54) |
| **4. Does ML model receive oracle variables?** | No, 0 oracle features in observed dataset | **PASSED** (0 oracle columns in `train.csv`) |
| **5. Action overlap in feature space?** | Multi-action occurrence verified per context | **PASSED** (Action overlap confirmed across all categories) |
| **6. Probabilistic outcomes?** | Bernoulli sampled with realistic noise | **PASSED** (Overall recovery rate = 42.02%) |
| **7. Hidden signal existence?** | Non-linear interactions present | **PASSED** (Std dev of true $P_{\text{rec}} = 0.3093$) |
| **8. ML learnability?** | Logistic Regression / Random Forest learns signal | **PASSED** (Baseline ML ROC AUC = 0.8387) |

---

## How to Reproduce Dataset & Validation

### Step 1: Generate Final 100,000 Dataset (Seed 42)
```bash
python src/data/generate_synthetic.py --config configs/synthetic_config.yaml --events 100000 --outdir data/synthetic
```

### Step 2: Run Unit Test Suite
```bash
python -m unittest tests/test_generator.py
python -m unittest tests/test_anti_circularity.py
```

### Step 3: Execute Validation Report
```bash
python -c "import pandas as pd; from src.data.validation import run_sanity_tests, print_validation_report; df_obs = pd.read_csv('data/synthetic/train.csv'); df_ora = pd.read_csv('data/synthetic/train_oracle.csv'); res = run_sanity_tests(df_obs, df_ora); print_validation_report(res)"
```
