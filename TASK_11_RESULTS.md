# TASK 11 TECHNICAL RESULTS — ML RECOVERY MODEL & ECONOMIC POLICY ADVISOR

## 1. Executive Objective
Task 11 implements the **ML Estimation Layer** ($P(\text{recovery} | X, a)$) and the **Expected Economic Value Policy Advisor** ($a^* = \arg\max_{a \in A_{\text{safe}}(X)} EV(a|X)$) for **O1 — Payment Failure Economic Recovery Advisor** (Razorpay Track 03 — AI Revenue Recovery).

The objective is to prove that an ML-driven economic policy advisor under hard safety constraints outperforms a competent deterministic decline-code baseline without circular evaluation.

---

## 2. Data Tier & Experimental Context
- **Data Tier**: **TIER C (Public structural data + synthetic recovery environment)**.
- **Observed Data**: 100,000 synthetic failure episodes (70,000 Train / 15,000 Val / 15,000 Test) generated in Task 10 under an $\epsilon$-greedy historical logging policy ($\epsilon = 0.30$).
- **No Ground-Truth Leakage**: Predictive models were trained strictly on observed context features $X$ and historical `logged_action`. Oracle columns (`SYNTHETIC_ORACLE_ONLY_*`), post-action outcomes, and post-action costs were strictly excluded.

---

## 3. Machine Learning Estimator Architecture
The core estimator models $P(\text{recovery} = 1 | X, \text{action})$ using 24 decision-time context features and the action as an explicit categorical variable.

### Evaluated Model Candidates (Validation Set: 15,000 Events)

| Model Candidate | Calibration | Validation ROC AUC | Validation Log Loss | Validation Brier Score | Mean Cal. Error | Selection Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | Uncalibrated | 0.8383 | 0.4570 | 0.1583 | 0.0098 | Candidate |
| **Logistic Regression** | Calibrated (Sigmoid) | 0.8383 | 0.4570 | 0.1583 | 0.0099 | Candidate |
| **Random Forest (d=10)** | Uncalibrated | 0.8400 | 0.4756 | 0.1616 | 0.0727 | Candidate |
| **Random Forest (d=10)** | Calibrated (Sigmoid) | 0.8403 | 0.4693 | 0.1601 | 0.0459 | Candidate |
| **HistGradientBoosting** | Uncalibrated | 0.8519 | 0.4441 | 0.1524 | 0.0206 | Candidate |
| **HistGradientBoosting** | **Calibrated (Sigmoid)** | **0.8584** | **0.4384** | **0.1494** | **0.0166** | **SELECTED OPTIMAL** |

**Selection Rationale**: `HistGradientBoosting (Calibrated)` achieved the lowest Brier Score (`0.1494`), lowest Log Loss (`0.4384`), highest ROC AUC (`0.8584`), and a low mean calibration error (`0.0130`).

---

## 4. Economic Policy Advisor Formulation
For any failure context $X$:
1. **Safety Gate Filtering**: Computes allowable safe actions $A_{\text{safe}}(X)$ via deterministic safety rules in [`src/data/safety.py`](file:///c:/Users/admin/Documents/Razorpay/src/data/safety.py).
2. **Probability Estimation**: Obtains $\hat{P}(\text{recovery} | X, a)$ for candidate actions $a \in A_{\text{safe}}(X)$.
3. **Economic Valuation**: Computes expected economic value for each safe candidate action:
   $$EV(a | X) = \hat{P}(\text{recovery} | X, a) \cdot V - C(a) - D(a) - F(a)$$
4. **Policy Selection**:
   $$a^* = \arg\max_{a \in A_{\text{safe}}(X)} EV(a | X)$$
5. **Confidence Level**:
   - `high`: EV margin over runner-up action $> \text{₹}50.0$ AND predicted recovery prob $> 0.40$ (or $a^* = \text{do\_nothing}$).
   - `medium`: EV margin $\ge \text{₹}10.0$.
   - `low`: EV margin $< \text{₹}10.0$.

---

## 5. Evaluation Results (Held-Out Test Split: 15,000 Events)

> **Split discipline.** The table in section 4 reports **validation** metrics: that split
> selected the winning candidate, so those numbers are optimistically biased. The figures
> below are the **held-out test** metrics, scored once after selection was frozen. Quote
> these as model quality.

### Pillar A: Predictive Model Quality (Held-Out Test Split)
- **ROC AUC**: `0.8600`  *(validation, used for selection: `0.8584`)*
- **Log Loss**: `0.4420`
- **Brier Score**: `0.1485`  *(validation, used for selection: `0.1494`)*
- **Mean Calibration Error**: `0.0130`

### Pillar B: SNIPS Off-Policy Estimator (NOT ground truth)

> SNIPS estimates policy value only from logged episodes where the target policy agrees
> with the historical policy. It is the deployment-style analogue - what a real rollout
> would have to rely on before running an experiment - but it uses a fraction of the data
> and carries wide uncertainty. Pillar C below is the authoritative benchmark.

- **Logged Policy Realized Mean EV**: **₹1,596.19** / event
- **Deterministic Baseline Policy SNIPS EV**: **₹1,676.60** / event (Coverage: 72.71%, ESS: 5,333.6, 95% CI ₹1,567.68-₹1,785.87)
- **O1 ML Policy SNIPS EV**: **₹2,415.74** / event (Coverage: 37.80%, ESS: 1,724.6, 95% CI ₹2,088.89-₹2,861.67)
- **Overlap diagnostics**: min logging propensity `0.075`, max importance weight `13.33`, no clipping applied
- **SNIPS minus direct true EV**: **+₹62.20** - estimator variance, **not** additional recovered value (well under one standard error of ₹201.53)

### Pillar C: Direct Ground-Truth Simulator Benchmark (AUTHORITATIVE)
> *Explicit Disclaimer: synthetic simulator benchmark - not production evidence.*

Every episode is scored against the hidden simulator. No matched subset, no importance
weights, no dropped rows.

- **Episodes scored**: **15,000 / 15,000** (0 missing ground truth)
- **Deterministic Baseline Policy EV**: **₹1,671.74** / event
- **O1 Economic Policy EV**: **₹2,353.54** / event
- **Oracle Best Achievable EV**: **₹2,356.66** / event
- **Net Uplift over Baseline**: **+₹681.80 / event (+40.78%)**
- **Policy Regret**: **₹3.12 / event** (99.87% of the oracle ceiling)
- **Per-event dominance violations**: **0** - `EV_true(O1) <= EV_true(oracle)` verified on every individual episode, not merely on average
- **Action matches oracle-best action**: 96.85%

### Pillar D: Safety Gate Enforcement
- **Safety Violation Count**: `0`
- **Safety Violation Rate**: **0.00%** (100% safety compliance across all 15,000 test events)

---

## 6. Action Selection Distribution

Read directly from `reports/task11_policy_evaluation.json` and `reports/task12_robustness.json`.

| Action | Logged Policy Share (%) | Deterministic Baseline Share (%) | O1 ML Policy Advisor Share (%) |
| :--- | :---: | :---: | :---: |
| `retry_now` | 23.71% | 38.89% | 0.04% |
| `retry_later` | 24.87% | 27.39% | 2.47% |
| `switch_method` | 13.09% | 3.98% | 67.85% |
| `update_information` | 11.51% | 14.33% | 14.23% |
| `do_nothing` | 26.82% | 15.41% | 15.41% |

O1 concentrates on `switch_method` because the simulator's hidden interactions (PSU night
maintenance, UPI peak-hour congestion, cross-border 3DS friction, high-value verification)
all reward switching the instrument over retrying the same one. The deterministic baseline,
which reads only the decline code, cannot see any of that.

---

## 7. Visualizations

Generated plots are saved under [`reports/figures/`](file:///c:/Users/admin/Documents/Razorpay/reports/figures/):
1. **Calibration Curve**: [`reports/figures/calibration_curve.png`](file:///c:/Users/admin/Documents/Razorpay/reports/figures/calibration_curve.png)
2. **Probability Distribution**: [`reports/figures/prob_distribution.png`](file:///c:/Users/admin/Documents/Razorpay/reports/figures/prob_distribution.png)
3. **Action Selection Share**: [`reports/figures/action_distribution.png`](file:///c:/Users/admin/Documents/Razorpay/reports/figures/action_distribution.png)
4. **Economic Performance Comparison**: [`reports/figures/ev_comparison.png`](file:///c:/Users/admin/Documents/Razorpay/reports/figures/ev_comparison.png)

---

## 8. Limitations & Disclaimers
1. **Tier C Synthetic Data**: All transactions, actions, recovery outcomes, and economic values are synthetic.
2. **Modeled Assumptions**: Costs ($C(a)$), penalties ($D(a)$), and friction costs ($F(a)$) represent domain-informed parameters rather than actual Razorpay production fee contracts.
3. **Off-Policy Evaluation Scope**: Off-Policy IPS results reflect evaluation within the synthetic randomized logging environment ($\epsilon = 0.30$).
4. **Non-Causal Claims**: Findings demonstrate architectural feasibility and learning capability within a controlled environment, not real-world Razorpay payment recovery uplift.

---

## 9. Conclusion
The Task 11 implementation proves that:
1. An ML model can accurately learn complex, non-linear contextual payment recovery probability functions ($P(\text{recovery}|X,a)$) without feature leakage or circular labels.
2. An Expected Economic Value policy advisor under strict safety pre-filtering delivers a substantial economic improvement over a deterministic rules baseline in this synthetic environment: **+₹681.80/event (+40.78%)** measured directly against the simulator across all 15,000 episodes, with **₹3.12/event** regret against the oracle ceiling. The SNIPS estimator independently corroborates the direction (+₹739.14/event) with a wide interval.
3. The system maintains 100% safety compliance while dynamically allocating recovery actions according to context-specific expected economics.
