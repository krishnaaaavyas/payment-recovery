# O1 Buildathon Judge Pitch Script (5 Minutes)

> **Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery**  
> **Project**: O1 — Payment Failure Economic Recovery Advisor  

---

## Pitch Timeline & Speaker Transcript

```text
0:00–0:30 │ Hook: The Economic Nature of Payment Failure
0:30–1:00 │ The Problem: Naive Retries Cause Revenue & Friction Loss
1:00–2:00 │ The O1 Solution: Constrained Economic Decision Agent
2:00–3:00 │ Live System Demo: Detect → Predict → Value → Constrain → Decide → Audit
3:00–4:00 │ Technical Architecture: Calibrated ML + Economics + Safety Gate
4:00–4:30 │ Empirical Results: +40.78% Net Uplift & 0% Safety Violations
4:30–5:00 │ Summary & Data Tier Disclosure
```

---

### [0:00–0:30] Hook — The Economic Nature of Payment Failure

> *"Judges, when an online payment fails, standard payment systems ask a binary question: 'Did this fail?' and execute a static retry rule. But in reality, payment failures are NOT binary—and retrying every failure is economically irrational.*  
> *A retry might recover revenue on a transient network glitch, but on an expired card or bank downtime, a retry wastes another attempt, increases merchant gateway fees, frustrates the customer, and risks account blocking.*  
> *The correct question is NOT 'Can we retry this payment?' but 'Which recovery intervention maximizes expected economic value while remaining safe and bounded?'"*

---

### [0:30–1:00] The Problem — Naive Retries Cause Revenue & Friction Loss

> *"Current decline-code policies operate deterministically: if a card fails, retry immediately; if a soft decline occurs, retry later. They ignore customer tenure, transaction value, issuer failure trends, and cumulative friction costs.*  
> *Without economic optimization, recoverable GMV is left on the table. But without safety constraints, ML models attempt illegal actions—like prompting users for card details during complete bank outages."*

---

### [1:00–2:00] The Solution — O1 Bounded Decision Agent

> *"We built **O1**, a post-payment-failure economic decision layer. O1 evaluates failed payments across 5 bounded actions: `retry_now`, `retry_later`, `switch_method`, `update_information`, and `do_nothing`.*  
> *O1 runs a 5-step decision loop:*  
> 1. **Detect** revenue at risk across 24 pre-decision context variables.  
> 2. **Predict** calibrated recovery probability $P(\text{recovery} \mid X, a)$.  
> 3. **Calculate** net Expected Economic Value $EV(a \mid X) = P \cdot V - C(a) - D(a) - F(a)$.  
> 4. **Constrain** actions via a deterministic Safety Gate $A_{\text{safe}}(X)$.  
> 5. **Decide** the optimal safe action, outputting an evidence-based explanation and immutable audit record."*

---

### [2:00–3:00] Live System Demonstration

> *"Let's look at the live O1 Operations Console.*  
> *[Navigate to Payment Queue]* Here we ingest a failed UPI payment episode (₹555.14, Authentication Failure).*  
> *[Click 'Analyze Recovery with O1']* Our FastAPI service computes probabilities across all 5 candidate interventions. It recommends `switch_method` with a 52.45% recovery probability and net Expected Economic Value of ₹276.17.*  
> *[Click 'Execute Action']* The simulator dispatches the prompt to the customer's checkout session.*  
> *[Click 'Inspect Audit Record']* Everything is logged to an immutable audit store recording candidate probabilities, net EV matrices, applied safety rules, and status."*

---

### [3:00–4:00] Technical Depth — Calibrated ML + Economics + Safety Gate

> *"Under the hood, O1 combines three core innovations:*  
> 1. **Calibrated Machine Learning**: A `HistGradientBoosting` classifier calibrated with sigmoid (Platt) scaling achieving a held-out test Brier Score of 0.1485 and ROC AUC of 0.8600.*  
> 2. **Net Economic Equation**: Incorporates transaction value $V$, direct action cost $C$, downside retry penalty $D$, and customer friction $F$.*  
> 3. **Safety Gate Architecture**: Enforces domain constraints before optimization. In our ablation study, removing the Safety Gate caused an **83.23% constraint-breach rate**. With O1's Safety Gate, safety violations remain **0.00%**."*

---

### [4:00–4:30] Empirical Results

> *"We evaluated O1 using Self-Normalized Importance Sampling (SNIPS) counterfactual evaluation on 15,000 test episodes:*  
> - **Deterministic Baseline EV**: ₹1,671.74 / event  
> - **O1 Economic Policy EV**: **₹2,353.54 / event**  
> - **Net Uplift**: **+40.78% (+₹681.80 / event)** measured directly against the simulator on all 15,000 episodes  
> - **Oracle Regret**: **₹3.12 / event** (99.87% of the oracle ceiling; O1 never beats the oracle on any individual episode)  
> - **Safety Violations**: **0.00%**."*

---

### [4:30–5:00] Conclusion & Data Tier Disclosure

> *"To summarize: O1 does not treat every failed payment as a retry opportunity. It treats recovery as an economic decision under safety constraints.*  
> *[Disclosure Statement]: As required by competition rules, our evaluation is conducted on a synthetic recovery environment derived from public Razorpay schemas. No production Razorpay customer data was used, and the executor is a simulation.*  
> *Thank you, and we welcome your questions."*
