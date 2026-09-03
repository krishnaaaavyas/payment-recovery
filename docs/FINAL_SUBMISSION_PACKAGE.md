# O1 — Payment Failure Economic Recovery Advisor

**Track 03 — AI Revenue Recovery**  
**Razorpay Buildathon 2026 Submission Package**  
**Public Repository:** [https://github.com/krishnaaaavyas/razorpay-payment-recovery-advisor](https://github.com/krishnaaaavyas/razorpay-payment-recovery-advisor)

---

## 1. PROJECT TITLE

**O1 — Payment Failure Economic Recovery Advisor**  
*Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery*

---

## 2. ONE-LINE PITCH

O1 evaluates failed payment episodes, predicts action-conditional recovery probabilities, calculates Net Expected Economic Value, and enforces hard deterministic domain safety rules to recommend optimal recovery interventions.

---

## 3. THE PROBLEM

Transaction failures in digital payments create significant, recoverable revenue loss for merchants and payment platforms. Traditional payment recovery relies primarily on static, blanket retry schedules or basic heuristic rules. These unconstrained approaches fail to consider payment context—such as failure origin, issuer category, transaction amount, customer payment tenure, or active bank outages. 

Consequently, naive retries generate excessive gateway fee overhead, exacerbate customer friction, and risk violating bank or regulatory policy limits (for instance, repeatedly attempting auto-retries during an active bank outage or retrying authentication failures without credential updates). 

Effective payment recovery cannot simply be treated as a brute-force retry problem; it must be framed as a **constrained economic decision-making problem** where every intervention balances recovery revenue against operational cost, customer friction, and strict safety constraints.

---

## 4. OUR SOLUTION

O1 implements a closed-loop, 7-stage decision architecture:

$$\text{DETECT} \longrightarrow \text{PREDICT} \longrightarrow \text{VALUE} \longrightarrow \text{CONSTRAIN} \longrightarrow \text{DECIDE} \longrightarrow \text{EXECUTE} \longrightarrow \text{AUDIT}$$

1. **DETECT:** Ingests rich context from failed payment episodes (e.g., failure taxonomy code, issuer category, transaction value, historical success rates, time since last success).
2. **PREDICT:** Uses a calibrated Gradient Boosting ML model to predict action-conditional recovery probabilities $P(\text{recovery} \mid X, a)$ for candidate recovery actions.
3. **VALUE:** Calculates Net Expected Economic Value $\text{EV}(a \mid X)$ for each candidate action by factoring transaction value, gateway execution cost, customer friction penalties, and failure penalties.
4. **CONSTRAIN:** Enforces hard, deterministic domain safety rules (the **Safety Gate**) to filter out illegal or policy-violating interventions *before* economic selection.
5. **DECIDE:** Selects the safe action that maximizes Net Expected Economic Value. If policy rules require human intervention, the decision status escalates to `ESCALATE`.
6. **EXECUTE:** Dispatches the recommended recovery action (e.g., scheduled retry, prompt payment method switch) via simulated execution endpoints.
7. **AUDIT:** Generates an immutable, structured audit log recording candidate evaluation matrices, safety clearance status, rationale, and execution output for complete compliance inspectability.

> **Architectural Separation:** Large Language Models (LLMs) are **not** placed in the critical decision or execution path. Probabilities are predicted by ML, safety constraints are enforced deterministically, economic value is computed mathematically, and policy selection is guaranteed bounded.

---

## 5. WHY THIS IS AN AI/ML PROJECT

Predicting whether a failed payment will recover under a specific recovery action cannot be solved with static heuristic tables due to complex, high-dimensional feature interactions across issuer behaviors, error steps, customer tenure, and time-of-day patterns.

O1 employs a **calibrated `HistGradientBoostingClassifier`** trained to estimate action-conditional recovery probabilities $P(\text{recovery} \mid X, a)$:
- **Input Vector ($X, a$):** 24 contextual features encompassing payment method, failure category, issuer bank tier, transaction value tier, historical customer success rate, and historical retry count.
- **Model Calibration:** Calibrated via Isotonic Regression / Sigmoid probability mapping to ensure output probabilities represent true empirical likelihoods.
- **Discriminative Performance:** Achieves **ROC AUC = 0.8600** and a **Brier Score = 0.1485** on test evaluation data.

The ML model provides objective probability estimates; deterministic domain logic then governs which actions are legal under regulatory and operational policies.

---

## 6. ECONOMIC DECISION FUNCTION

O1 optimizes for **Net Expected Economic Value (EV)** rather than gross recovery rate alone. Maximizing gross recovery without considering cost leads to economically irrational decisions (such as spending ₹50 in gateway retries and customer friction to recover a ₹30 transaction).

The Net Expected Economic Value for action $a$ given context $X$ is defined as:

$$\text{EV}(a \mid X) = P(\text{recovery} \mid X, a) \cdot V - C(a) - D(a) - F(a)$$

Where:
- $V =$ Transaction Order Value (INR).
- $P(\text{recovery} \mid X, a) =$ Model-predicted probability of successful payment completion under action $a$.
- $C(a) =$ Action Execution Cost (e.g., API gateway fee, SMS notification dispatch cost).
- $D(a) =$ Customer Friction Penalty (quantified inconvenience or checkout disruption score).
- $F(a) =$ Failure Penalty (cost penalty incurred if the action fails).

The policy selects the optimal action $a^*$ from the set of safe actions $\mathcal{A}_{\text{safe}}(X)$:

$$a^* = \arg\max_{a \in \mathcal{A}_{\text{safe}}(X)} \text{EV}(a \mid X)$$

---

## 7. SAFETY GATE

The **Safety Gate** acts as a hard deterministic pre-filter. It evaluates context $X$ against domain policy rules to determine the subset of safe, permitted interventions $\mathcal{A}_{\text{safe}}(X)$:

$$\mathcal{A}_{\text{safe}}(X) \subseteq \mathcal{A}_{\text{all}}$$

Unsafe candidate actions are stripped **before** economic ranking occurs, ensuring that an action with high potential economic value can never be selected if it violates domain safety bounds.

### Real Domain Safety Rule Examples:
- `EXCLUDE_RETRY_ON_OUTAGE`: Excludes `retry_now` during active bank issuer outages or network degradation.
- `EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES`: Excludes `update_information` when failure is caused by network timeouts or gateway errors (preventing unnecessary customer credential re-entry).
- `EXCLUDE_SWITCH_ON_UPI_DECLINE`: Blocks invalid payment method switching when failure is due to explicit user PIN cancellation.

### Benchmark Safety Performance:
- **O1 Constrained Policy Safety Violations:** **0.00%** (0 / 15,000 evaluated test episodes).
- **Unconstrained Ablation (A3 - No Safety Gate):** Causes an **83.23% safety violation rate** under identical test conditions.

*Note: The 0.00% safety violation rate demonstrates the efficacy of the deterministic safety layer within the synthetic evaluation environment; it does not claim real-world zero operational risk.*

---

## 8. RESULTS & SCIENTIFIC EVALUATION

Authoritative evaluation metrics computed on $N = 15,000$ test episodes (sourced from [`../reports/task11_policy_evaluation.json`](../reports/task11_policy_evaluation.json)):

| Metric Category | Metric Name | Value | Description |
|---|---|---|---|
| **Direct Ground-Truth Simulator** | Baseline Policy EV | **₹1,671.74** / event | Standard static retry policy |
| | **O1 Policy EV** | **₹2,353.54** / event | O1 bounded economic policy |
| | Oracle Best EV | **₹2,356.66** / event | Theoretical optimal action selection |
| | Policy Regret | **₹3.12** / event | Difference between Oracle and O1 |
| | **Policy Efficiency** | **99.87%** | $\text{EV}_{\text{O1}} / \text{EV}_{\text{Oracle}}$ ratio |
| **Economic Impact** | **Net EV Uplift (Absolute)** | **+₹681.80** / event | Net economic gain per failure event |
| | **Net EV Uplift (Relative)** | **+40.78%** | Percentage improvement over Baseline |
| **Safety & Policy** | **Safety Violation Rate** | **0.00%** | 0 / 15,000 safety rule violations |
| **Model Quality** | Calibrated ROC AUC | **0.8600** | Probability ranking performance |
| | Brier Score | **0.1485** | Probability calibration accuracy |
| **Off-Policy Estimation** | **SNIPS Off-Policy EV** | **₹2,415.74 ± ₹201.53** | Self-Normalized Importance Sampling (95% CI) |

*Note: SNIPS provides an off-policy sample estimate from logged evaluation data, while the Direct Simulator computes exact ground-truth population metrics across the synthetic evaluation environment.*

---

## 9. DATA & SCIENTIFIC DISCLOSURE

> **TIER C — Synthetic Evaluation Environment**

- **Environment Nature:** All datasets, payment events, failure rates, and issuer behaviors were generated within a controlled, synthetic evaluation environment.
- **No Production Data:** No live Razorpay customer data, merchant records, or production API credentials were used.
- **Purpose:** The synthetic environment enables rigorous, reproducible evaluation of off-policy ML estimators, safety ablations, and economic optimization.
- **Interpretation:** Results demonstrate the validity of the O1 methodology and software architecture under simulated conditions; they should **not** be interpreted as measured production performance on live Razorpay payment traffic.

---

## 10. LIVE DEMO STORY (PRIMARY WALKTHROUGH)

The primary operator demo walkthrough uses payment event `pay_evt_00004778`:

1. **Open Payments Queue (`/queue`):** Operator views failed payment episodes. `pay_evt_00004778` is listed with Amount = **₹555.14**, Method = **UPI Intent**, Failure Reason = **Auth Failure** (`authentication_failure`).
2. **Review Decision (`/inspector`):** Operator clicks **Review Decision**. O1 evaluates candidate actions and displays:
   - **Recommended Action:** `SWITCH PAYMENT METHOD` (bold prominent display)
   - **Expected Economic Value:** **₹259.46** (emerald text)
   - **Recovery Probability:** **49.44%**
   - **Plain-Language Rationale:** *"Selected action 'switch_method' yields highest expected economic value (₹259.46) while remaining within policy limits."*
3. **Inspect Safety Checks:** Operator verifies the safety clearance checklist:
   - `✓ Permitted by domain safety rules (EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES)`
   - `✓ No active bank outage or network conflict restriction`
   - `✓ Customer friction within policy bounds`
4. **Execute Action:** Operator clicks **Execute Recommended Action**. System returns simulated execution confirmation: **Status: SCHEDULED** (`exec_44e9a2ad`).
5. **Inspect Audit Trail (`/audit`):** Operator clicks **View Audit Record**. Immutable audit log shows decision status `APPROVED`, selected action `switch_method`, candidate action evaluation matrix, and timestamp.
6. **Review Scientific Evidence (`/evaluation`):** Operator checks headline benchmark metrics (**+40.78% Net EV Uplift**, **0.00% Safety Violations**).

---

## 11. SECOND SCENARIO (CONTEXTUAL ADAPTABILITY)

To demonstrate that O1 adapts interventions dynamically based on failure context rather than applying static retries, consider payment event `pay_evt_00034382`:

- **Payment ID:** `pay_evt_00034382`
- **Method:** `UPI Intent`
- **Failure Category:** `upi_decline` (User PIN cancellation)
- **O1 Recommendation:** `RETRY LATER`
- **Decision Status:** `ESCALATE` (Flagged for human operator review/scheduling)
- **Expected EV:** **₹513.37**
- **Recovery Probability:** **54.90%**

*Key Takeaway:* Unlike `pay_evt_00004778` (where `switch_method` was recommended), O1 recognizes that a UPI user decline should not prompt an immediate method switch, selecting a delayed retry and escalating the episode to prevent customer friction.

---

## 12. ARCHITECTURE OVERVIEW

O1 is built as a production-oriented, decoupled prototype:

```text
[ Failed Payment Event ]
           │
           ▼
┌──────────────────────┐
│  Validation & Schema │ (Pydantic API contracts)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     Safety Gate      │ (Deterministic domain safety rules)
└──────────┬───────────┘
           │ Safe Actions Filtered
           ▼
┌──────────────────────┐
│     ML Predictor     │ (Calibrated HistGradientBoosting P(rec|X,a))
└──────────┬───────────┘
           │ Probabilities Calculated
           ▼
┌──────────────────────┐
│    EV Calculator     │ (Net Expected Economic Value Formulation)
└──────────┬───────────┘
           │ EV Ranked
           ▼
┌──────────────────────┐
│   Policy Advisor     │ (Optimal Action Selection & Rationale)
└──────────┬───────────┘
           │ Decision Formed
           ▼
┌──────────────────────┐
│ Simulated Executor   │ (Bounded Execution API Endpoint)
└──────────┬───────────┘
           │ Executed
           ▼
┌──────────────────────┐
│     Audit Store      │ (Immutable Decision Audit Logger)
└──────────────────────┘
```

- **Backend:** FastAPI (Python 3.11), Pydantic v2, Scikit-Learn, Joblib, Pytest.
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React.

---

## 13. WHAT MAKES O1 DIFFERENT

1. **Net Economic Value vs. Gross Recovery:** Maximizes net financial recovery after accounting for gateway fees, failure costs, and customer friction penalties.
2. **Hard Safety Constraints Before Optimization:** Enforces strict domain safety rules prior to economic ranking, preventing high-EV but policy-violating retries.
3. **Decoupled Architecture:** Separates probabilistic ML estimation, deterministic safety logic, economic calculation, and execution.
4. **Complete Auditability:** Every decision produces a structured audit record documenting candidate evaluation matrices and safety rule clearance.
5. **Rigorous Benchmark Evaluation:** Evaluated against an Oracle optimal policy ($99.87\%$ efficiency) and tested with safety gate ablations.

---

## 14. LIMITATIONS

- **Synthetic Evaluation Environment:** Evaluated on synthetic data; performance metrics reflect simulated environment conditions.
- **Simulated Execution:** Action execution is simulated via API endpoints without live money movement or production payment gateway dispatch.
- **Production Deployment Requirements:** Transitioning to production would require integration with live Razorpay event streams, real-time issuer outage feeds, merchant policy customization, and continuous model monitoring.

---

## 15. WHY NOT AN LLM AGENT FOR THE DECISION PATH?

While Large Language Models excel at natural language reasoning and operator explanation, putting an LLM in the core payment decision path introduces latency, non-deterministic outputs, hallucination risks, and difficulty in guaranteeing strict safety compliance.

O1 keeps the critical decision path **deterministic, mathematical, and fully auditable**:
- **ML** handles numerical probability estimation.
- **Safety Gate** enforces hard deterministic rules.
- **EV Function** computes mathematical economic value.
- **Policy Engine** selects the best safe action.

LLMs or natural language interfaces can be used for summary explanations, but core payment interventions remain strictly bounded.

---

## 16. LIKELY JUDGE QUESTIONS & VERBAL ANSWERS

**Q1. Why is O1 better than a simple retry rule?**  
*Answer:* Simple retry rules ignore context, costs, and friction. O1 predicts recovery probability based on 24 contextual features, calculates net economic value after costs, and enforces safety bounds to avoid useless or dangerous retries.

**Q2. Why use ML here?**  
*Answer:* Issuer behaviors, failure categories, and customer tenure interact non-linearly. ML predicts action-conditional recovery probability $P(\text{recovery} \mid X, a)$ far more accurately than static lookup tables.

**Q3. Why not use an LLM for decisions?**  
*Answer:* Payment recovery requires low latency, mathematical optimization, and guaranteed safety compliance. O1 uses ML for probabilities and code for safety/EV, ensuring 100% deterministic safety bounds.

**Q4. How do you prevent unsafe recovery actions?**  
*Answer:* The Safety Gate pre-filters candidate actions before economic selection. Unsafe actions are stripped upfront, resulting in 0.00% safety violations across 15,000 test episodes.

**Q5. What happens during a bank outage?**  
*Answer:* The Safety Gate applies `EXCLUDE_RETRY_ON_OUTAGE`, blocking immediate retries and selecting either delayed retry or operator escalation.

**Q6. How do you measure economic improvement?**  
*Answer:* We compute Net Expected Economic Value ($\text{EV} = P \cdot V - \text{Cost} - \text{Friction}$) and compare O1 against a standard baseline retry policy. O1 achieves a +40.78% net EV uplift.

**Q7. How do you know the ML model is calibrated?**  
*Answer:* We evaluate probability calibration using Brier score (0.1485) and ROC AUC (0.8600) on test evaluation data.

**Q8. What does 99.87% efficiency mean?**  
*Answer:* It means O1 achieves 99.87% of the maximum theoretical economic recovery value attainable by an all-knowing Oracle policy.

**Q9. Why is the data synthetic?**  
*Answer:* Public payment failure datasets with ground-truth counterfactuals do not exist due to commercial privacy. Synthetic data allows full population benchmarking, safety ablations, and reproducible research.

**Q10. What would you do with real Razorpay data?**  
*Answer:* We would train the classifier on historical Razorpay transaction logs, connect live bank outage feeds, configure merchant-specific friction parameters, and run A/B testing.

**Q11. Is execution real?**  
*Answer:* Execution is simulated via API endpoints to demonstrate end-to-end operational dispatch without live money movement.

**Q12. How would this scale in production?**  
*Answer:* The architecture is lightweight (FastAPI + Scikit-Learn inference <10ms per event), allowing sub-second decision making at scale.

---

## 17. 30-SECOND SPOKEN PITCH

> "Transaction failures cost merchants millions in lost revenue, but naive retries waste money on gateway fees and frustrate customers. O1 is an AI Revenue Recovery Advisor built for Razorpay Track 03. It predicts recovery probability using a calibrated ML model, calculates Net Expected Economic Value after costs, and enforces hard Safety Gates to block unsafe retries. On 15,000 test episodes in a synthetic evaluation environment, O1 delivered a +40.78% net EV uplift with zero safety violations, achieving 99.87% of Oracle efficiency."

---

## 18. 2-MINUTE SPOKEN PITCH

> "Payment failures are a major leak in digital commerce. Today, most gateways rely on static retry schedules. But retrying a payment without context is inefficient: retrying during a bank outage wastes fees, and retrying authentication errors without new credentials annoys customers.
>
> O1 transforms payment recovery into a constrained economic decision problem. When a failure occurs, O1 ingests 24 contextual features—including failure codes, issuer bank tier, and customer tenure. 
>
> First, our Safety Gate evaluates hard policy rules, stripping out illegal or unsafe actions before any optimization happens. 
>
> Next, a calibrated Gradient Boosting ML model predicts the recovery probability for each safe action. 
>
> Then, our economic engine calculates Net Expected Economic Value—factoring in transaction amount, gateway fees, and customer friction penalties—and selects the action that maximizes net return.
>
> In our synthetic benchmark of 15,000 episodes, O1 achieved a +40.78% net EV uplift over standard retries with 0.00% safety violations, capturing 99.87% of theoretical Oracle value. O1 proves that smart, safe economic decisions recover more revenue at lower cost."

---

## 19. 5-MINUTE DEMO SCRIPT

| Time | Screen / Action | Spoken Words | Objective |
|---|---|---|---|
| **00:00–00:30** | Open **Payments Queue** (`/queue`) | *"Welcome to O1. Here in the Payments Queue, payment operations teams can view failed transactions in real time. Notice transaction `pay_evt_00004778` for ₹555.14, which failed due to authentication failure."* | Establish context & operational view. |
| **00:30–01:15** | Click **Review Decision** | *"When we select this payment, O1 evaluates available recovery interventions. Instead of blindly retrying, O1 analyzes failure context and computes net economic value."* | Introduce contextual decision making. |
| **01:15–02:00** | View **Decision Inspector** (`/inspector`) | *"O1 recommends 'SWITCH PAYMENT METHOD' with an Expected Economic Value of ₹259.46 and a 49.44% recovery probability. Notice the plain-language rationale explaining why this action maximizes net return."* | Show ML prediction & EV calculation. |
| **02:00–02:30** | Point out **Safety Checks** | *"Crucially, before economic ranking, O1's Safety Gate checked domain policy rules. Immediate retry was ruled out due to technical failure constraints, guaranteeing zero safety violations."* | Highlight Safety Gate pre-filtering. |
| **02:30–03:00** | Click **Execute Recommended Action** | *"We execute the recommendation. O1 dispatches a simulated method switch prompt to the customer session and confirms status: SCHEDULED."* | Demonstrate execution dispatch. |
| **03:00–03:45** | Click **View Audit Record** (`/audit`) | *"Every decision produces an immutable audit record (`dec_bbea3051`), showing the candidate evaluation matrix, safety clearance, and execution log for compliance."* | Demonstrate auditability & compliance. |
| **03:45–04:30** | Navigate to **Evaluation** (`/evaluation`) | *"On our evaluation benchmark of 15,000 episodes, O1 delivers a +40.78% net EV uplift over standard retries with 0.00% safety violations, achieving 99.87% of Oracle efficiency."* | Present headline scientific evidence. |
| **04:30–05:00** | Point to **Tier C Disclosure** | *"All metrics reflect a controlled Tier C synthetic evaluation environment, proving the architecture and economic methodology. Thank you!"* | Disclose synthetic environment & wrap up. |

---

## 20. FINAL CLOSING STATEMENT

O1 demonstrates that payment failure recovery should not be approached through unconstrained retries or opaque language generation. By framing recovery as constrained economic decision-making—combining calibrated machine learning, mathematical economic valuation, and hard deterministic safety bounds—O1 provides a transparent, safe, and highly effective model for digital revenue recovery.

---

## 21. IMPORTANT LINKS & REFERENCES

- **Public GitHub Repository:** [https://github.com/krishnaaaavyas/razorpay-payment-recovery-advisor](https://github.com/krishnaaaavyas/razorpay-payment-recovery-advisor)
- **Project Documentation & References:**
  - [`../README.md`](../README.md) — Project Overview & Quick Start
  - [`DEMO.md`](DEMO.md) — Complete Demonstration Guide
  - [`PITCH_5_MINUTES.md`](PITCH_5_MINUTES.md) — 5-Minute Spoken Pitch Script
  - [`PITCH_SLIDES.md`](PITCH_SLIDES.md) — Slide Deck Outline
  - [`architecture.md`](architecture.md) — Technical Architecture & EV Specification
  - [`../DATASET_CARD.md`](../DATASET_CARD.md) — Data Tier & Schema Declaration
  - [`../SYNTHETIC_GENERATION.md`](../SYNTHETIC_GENERATION.md) — Synthetic Environment Generation Design
  - [`../TASK_15_SUBMISSION_PACKAGE.md`](../TASK_15_SUBMISSION_PACKAGE.md) — Milestone Submission Package
  - [`../reports/task11_policy_evaluation.json`](../reports/task11_policy_evaluation.json) — Authoritative Policy Evaluation Results
  - [`../reports/task12_robustness.json`](../reports/task12_robustness.json) — Robustness & Sensitivity Analysis
