# Payment Recovery Technical Reviewer Demo Guide

> **Built for Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**
> **Project**: Payment Recovery

---

## 1. Local Environment Prerequisites

Ensure **Python 3.11+** and **Node.js v18+ / v22+** are installed.

### Terminal 1: Launch FastAPI Backend Service
```bash
# Run from the repository root
uvicorn src.api.app:app --reload --port 8000
```
*Health Check*: Open `http://localhost:8000/health` (should return `{"status": "ok", ...}`).

### Terminal 2: Launch Operations Dashboard
```bash
# From the frontend directory
cd frontend
npm run dev
```
*Dashboard URL*: Open `http://localhost:5173` in your browser.

---

## 2. Step-by-Step 60-Second Demo Walkthrough

### Step 1: System Overview & Economic Value (+40.78% Uplift)
- Open `http://localhost:5173`.
- **Observe**: Top metric cards showing:
  - **O1 Policy Expected Value (direct simulator)**: **₹2,353.54 / event**
  - **Baseline Policy Expected Value (direct simulator)**: **₹1,671.74 / event**
  - **Net Economic Uplift**: **+40.78% (+₹681.80 / event)**, measured on all 15,000 held-out episodes
- **Observe**: Persistent Tier C Synthetic Environment disclosure banner.

### Step 2: Ingest & Filter Failed Payments
- Click **"Payment Queue"** tab.
- Filter by `Payment Method: UPI Intent` and `Failure Category: Network Timeout`.
- Select episode `pay_evt_88840335` (Transaction Amount: ₹555.14, UPI Intent, Authentication Failure) and click **"Analyze"**.

### Step 3: Trigger AI Recovery Decision (POST /decide)
- On the **Decision Inspector** view, click **"Analyze Recovery with O1"**.
- **Observe**: The FastAPI backend evaluates the 24-feature context and returns:
  - **Recommended Action**: `switch_method`
  - **Recovery Probability $P(\text{rec}|X,a)$**: `52.45%`
  - **Expected Economic Value $EV(a|X)$**: `₹276.17`
  - **Decision Status**: `APPROVED`
  - **Safety Gate Rule**: `EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES`
  - **Evidence Rationale**: Evidence-based deterministic explanation text.

### Step 4: Execute Action Simulation (POST /execute)
- Click **"Execute Action"**.
- **Observe**: Execution status returns `SCHEDULED` ("Simulated payment method switch prompt dispatched to customer checkout session").
- **Notice**: Clear simulation disclaimer ("Simulation only — No real Razorpay or gateway API called").

### Step 5: Inspect Immutable Decision Audit Log (GET /audit/{id})
- Click **"Inspect Full Decision Audit Record"**.
- **Observe**: Complete candidate evaluation matrix showing probabilities and net EV across all 5 candidate actions (`retry_now`, `retry_later`, `switch_method`, `update_information`, `do_nothing`).
- Toggle **"View Raw JSON"** to view the immutable audit payload.

### Step 6: Review Safety Gate Ablation Finding (0.00% vs 83.23%)
- Click **"Overview"** or **"Evaluation Metrics"** tab.
- **Observe**: Safety Gate Architectural Guarantee:
  - **Full O1 Architecture**: **0.00% Safety Violations** (0 / 15,000 episodes).
  - **Without Safety Gate (Ablation A3)**: **83.23% constraint breaches** (12,485 episodes). Note this variant also scores ~₹101/event *higher* on simulated EV - the gate is a compliance cost, and we say so.
- **Finding**: Proves that unconstrained economic optimization without Safety Gate filtering causes severe compliance breaches by prompting users during technical bank outages.

---

> [!IMPORTANT]
> **TIER C DISCLOSURE**: All recovery probabilities, expected economic values, and policy performance metrics are evaluated on synthetic test datasets. They do not represent measured Razorpay production performance or real customer behavior. The executor is a simulation and does NOT perform real money movement.
