# O1 Pitch Slide Deck Layout (8 Slides)

> **Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery**  
> **Project**: O1 — Payment Failure Economic Recovery Advisor  

---

## Slide 1: Title Slide
- **Headline**: O1 — Payment Failure Economic Recovery Advisor
- **Subtitle**: Turning Payment Failures into Bounded Economic Decisions
- **Metadata**: Razorpay Buildathon 2026 | Track 03 — AI Revenue Recovery
- **Key Visual**: O1 Decision Loop Icon ($\text{Predict} \rightarrow \text{Value} \rightarrow \text{Constrain} \rightarrow \text{Decide}$)

---

## Slide 2: The Problem
- **Headline**: Payment Failure $\neq$ One-Size-Fits-All Retry
- **Bullet Points**:
  - Naive retries waste customer retry caps and incur gateway penalty fees.
  - Static decline-code policies ignore transaction value, customer tenure, and friction.
  - Unconstrained ML models attempt illegal actions during bank outages.
- **Key Takeaway**: Recovery is an economic optimization problem under hard safety constraints.

---

## Slide 3: The O1 Solution
- **Headline**: The O1 Decision Lifecycle
- **Visual Diagram**:
  $$\text{Detect Context} \longrightarrow \text{Predict } P(\text{rec}) \longrightarrow \text{Calculate Net EV} \longrightarrow \text{Safety Gate Filter} \longrightarrow \text{Bounded Decision} \longrightarrow \text{Audit Log}$$
- **5 Bounded Actions**: `retry_now`, `retry_later`, `switch_method`, `update_information`, `do_nothing`

---

## Slide 4: System Architecture
- **Headline**: Multi-Layer Production Architecture
- **Layer Diagram**:
  - **Data Layer**: 24-feature context vectors from public schema taxonomy
  - **Predictive Layer**: Sigmoid-calibrated `HistGradientBoosting` classifier (held-out test ROC AUC 0.8600)
  - **Economic Layer**: Expected Economic Value Engine
  - **Safety Layer**: Hard deterministic Safety Gate
  - **Interface Layer**: FastAPI REST Service + React Operations Console

---

## Slide 5: The Economic Valuation Engine
- **Headline**: Maximizing Net Expected Economic Value
- **Core Formula**:
  $$EV(a \mid X) = \hat{P}(\text{recovery} \mid X, a) \cdot V - C(a) - D(a) - F(a)$$
- **Parameters**:
  - $V$: Transaction Order Amount (INR)
  - $C(a)$: Direct Retry / Gateway Cost
  - $D(a)$: Downside Penalty
  - $F(a)$: Customer Friction Cost

---

## Slide 6: Safety by Architecture
- **Headline**: Safety Gate Compliance vs Ablation
- **Visual Bar Comparison**:
  - **Full O1 Architecture (With Safety Gate)**: **0.00% Safety Violations** (0 / 15,000 episodes)
  - **Ablation A3 (Without Safety Gate)**: **83.23% constraint breaches** (12,485 episodes)
- **Insight**: Safety must be an architectural boundary prior to economic optimization.

---

## Slide 7: Synthetic Evaluation & Performance
- **Headline**: Off-Policy SNIPS Benchmark & Oracle Regret
- **Key Metrics Table**:
  - **Baseline EV (direct simulator)**: ₹1,671.74 / event
  - **O1 Economic Policy EV**: **₹2,353.54 / event** (+40.78% / +₹681.80 per event)
  - **Oracle Best Achievable EV**: ₹2,356.66 / event
  - **Oracle Regret**: **₹3.12 / event** (99.87% of the oracle ceiling)
- **Robustness**: Performance ranking stable across 6 economic perturbations and 3 distribution shifts.

---

## Slide 8: Conclusion & Data Tier Disclosure
- **Headline**: Bounded AI Revenue Recovery
- **Closing Statement**: *"O1 does not treat every failed payment as a retry opportunity. It treats recovery as an economic decision under safety constraints."*
- **Tier C Disclosure Badge**: Recovery probabilities, expected values, and policy performance metrics are evaluated on synthetic test datasets. They do not represent measured Razorpay production performance. The executor is a simulation.
