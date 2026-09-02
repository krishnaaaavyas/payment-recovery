# Full-Stack Demonstration & Reviewer Pitch Script

> **Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery**  
> **Project**: O1 — Payment Failure Economic Recovery Advisor  

---

## Technical Pitch Walkthrough (2–3 Minutes)

```text
00:00 — Overview: Problem Statement & +40.78% Economic Gains
00:25 — Payment Failure Ingestion & Queue Filtering
00:45 — Real-Time AI Decision Engine (POST /decide)
01:15 — Safety Gate Enforcement (0.00% vs 83.23% Ablation)
01:35 — Simulated Action Execution (POST /execute)
01:55 — Immutable Decision Audit Trail (GET /audit/{id})
02:15 — Off-Policy SNIPS & Oracle Benchmark Verification
```

---

### Step 1: Launch Local Environment

#### Terminal 1: Start FastAPI Backend Service
```bash
# Directory: C:\Users\admin\Documents\Razorpay
uvicorn src.api.app:app --reload --port 8000
```

#### Terminal 2: Start React Operations Dashboard
```bash
# Directory: C:\Users\admin\Documents\Razorpay\frontend
npm run dev
```
Open browser at `http://localhost:5173`.

---

### Step 2: Pitch Script & Action Flow

#### [00:00 - 00:25] 1. Overview Dashboard
- **Presenter**: *"Payment failures create substantial recoverable revenue loss. Standard decline-code rules apply static actions, while unconstrained ML models violate compliance boundaries. O1 estimates recovery probability $P(\text{recovery}|X, a)$ and net Expected Economic Value $EV(a|X)$ to select the optimal safe intervention."*
- **Action**: Highlight top metric cards:
  - **O1 Policy EV (direct simulator)**: **₹2,353.54 / event** vs Baseline **₹1,671.74 / event** (+40.78% / +₹681.80 per event, all 15,000 episodes).
  - **Safety Gate Feature Comparison**: **0.00% safety violations** under O1 vs **83.23% constraint breaches** (12,485 episodes) without Safety Gate constraints (Ablation A3).

#### [00:25 - 00:45] 2. Payment Failure Queue
- **Presenter**: *"Here we see active failed payment episodes ingested from our synthetic test evaluation dataset. We can filter by method, failure category, or order amount."*
- **Action**: Click **"Payment Queue"** tab. Filter by `UPI Intent` and `Network Timeout`. Select episode `pay_evt_88840335` (Amount ₹555.14, UPI Intent, Authentication Failure) and click **"Analyze"**.

#### [00:45 - 01:15] 3. Decision Inspector (POST /decide)
- **Presenter**: *"Clicking 'Analyze Recovery with O1' triggers our backend FastAPI decision service. The engine ingests the 24-feature context, filters candidate actions via the Safety Gate, computes recovery probabilities and net EV, and returns a safe, bounded decision."*
- **Action**: Click **"Analyze Recovery with O1"**. Review decision output:
  - **Recommended Action**: `switch_method`
  - **Recovery Probability**: `52.45%`
  - **Expected Value**: `₹276.17`
  - **Status**: `APPROVED`
  - **Safety Rule**: `EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES`
  - **Rationale**: Evidence-based explanation detailing why `switch_method` maximizes net economic return over safe alternatives.

#### [01:15 - 01:35] 4. Simulated Action Execution (POST /execute)
- **Presenter**: *"Notice our execution control: execution is strictly bounded to approved safe decisions. The simulator dispatches the action without calling real Razorpay or gateway APIs."*
- **Action**: Click **"Execute Action"**. Show execution response status `SCHEDULED` ("Simulated payment method switch prompt dispatched to customer checkout session").

#### [01:35 - 01:55] 5. Immutable Audit Trail (GET /audit/{id})
- **Presenter**: *"Every automated decision generates an immutable audit record for compliance and post-hoc inspection."*
- **Action**: Click **"Inspect Full Decision Audit Record"**. Show the 5-action probability/EV candidate evaluation matrix and toggle **"View Raw JSON"**.

#### [01:55 - 02:15] 6. Scientific Evaluation Metrics
- **Presenter**: *"Finally, our evaluation dashboard confirms model predictive quality (held-out test ROC AUC 0.8600, Brier Score 0.1485), near-zero theoretical oracle regret (₹0.94/event), and performance ranking stability across economic perturbations and distribution shifts."*
- **Action**: Click **"Evaluation Metrics"** tab. Point out persistent Tier C synthetic evaluation disclosure.

---

> [!IMPORTANT]
> **TIER C DISCLOSURE**: All probabilities, economic values, and policy performance metrics are evaluated on synthetic test datasets. They do not represent measured Razorpay production performance or real customer behavior. The executor is a simulation and does NOT perform real money movement.
