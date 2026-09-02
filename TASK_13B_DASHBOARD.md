# Task 13B — Recovery Operations Dashboard Documentation

> **Razorpay Buildathon — Track 03: AI Revenue Recovery**  
> **Project**: O1 — Payment Failure Economic Recovery Advisor  

---

## 1. Architecture & Design Direction

Task 13B delivers an enterprise-grade **Recovery Operations Dashboard** built with **React**, **TypeScript**, and **Vite**.

```
                           FRONTEND (React + TypeScript + Vite)
                                          │
    ┌───────────────────┬─────────────────┼───────────────────┬──────────────────┐
    ▼                   ▼                 ▼                   ▼                  ▼
 Overview         Payment Queue   Decision Inspector     Audit Trail         Evaluation
 Dashboard         (50 events)    (Interactive AI)     (Full Snapshots)    (Off-Policy SNIPS)
    │                   │                 │                   │                  │
    └───────────────────┴─────────────────┼───────────────────┴──────────────────┘
                                          │ HTTP REST API (Fetch Client)
                                          ▼
                         FastAPI Backend (src/api/app.py)
                                          │
                                          ▼
                           RecoveryAgent Decision Engine
                                          │
                           PolicyAdvisor (Authoritative)
```

### Critical Architectural Constraint
**The frontend strictly acts as a presentation and interaction layer.** It contains **ZERO** duplicate recovery prediction, EV optimization, safety gate, stopping rule, or policy ranking logic. The backend FastAPI service remains authoritative for all decision and execution operations.

---

## 2. Component Structure

```text
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── .env.example
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── types/
    │   └── api.ts
    ├── services/
    │   └── api.ts
    └── components/
        ├── Header.tsx            # Title, health status, Tier C synthetic disclosure badge
        ├── Navigation.tsx        # Responsive navigation tabs
        ├── Overview.tsx          # 30-sec summary, EV comparison, safety ablation (live from /reports/summary)
        ├── PaymentQueue.tsx      # Ingested synthetic failure episodes table with filters
        ├── DecisionInspector.tsx # Real-time POST /decide & POST /execute interaction
        ├── AuditTrail.tsx        # Immutable decision record lookup (GET /audit/{id})
        └── Evaluation.tsx        # Direct benchmark, SNIPS + CIs, ablation, robustness (live from /reports/summary)
```

---

## 3. Core Dashboard Views

### 1. Overview Dashboard
- **Aggregate Revenue at Risk**: 15,000 synthetic test payment failure episodes.
- **Direct ground-truth EV (authoritative)**: Baseline **₹1,671.74** vs O1 Policy **₹2,353.54** (+40.78% / +₹681.80 per event). SNIPS estimator shown alongside with its 95% interval.
- **Recommended Action Share**: rendered from `reports/task11_policy_evaluation.json` - currently `switch_method` (67.85%), `do_nothing` (15.41%), `update_information` (14.23%), `retry_later` (2.47%), `retry_now` (0.04%).
- **Safety Gate Feature Comparison**: **0.00% safety violations** under the full O1 architecture vs **83.23%** (12,485 constraint breaches) without Safety Gate constraints (Ablation A3).

### 2. Payment Failure Queue
- Interactive table displaying synthetic failure episodes fetched from `GET /events?limit=50`.
- Supports searching by Payment ID / Failure Code and filtering by payment method and failure category.
- Primary **"Analyze"** action button to evaluate any episode.

### 3. Decision Inspector
- Displays full 24-feature payment context snapshot.
- Invokes backend `POST /decide` endpoint.
- Renders:
  - **Selected Safe Action**: `retry_now`, `retry_later`, `switch_method`, `update_information`, `do_nothing`.
  - **Recovery Probability**: $P(\text{rec}|X,a)$.
  - **Net Expected Value**: $EV(a|X)$ in INR.
  - **Model Confidence**: `high`, `medium`, or `low`.
  - **Safety Gate Clearance**: Applied constraint description (`safety_rule`).
  - **Status & Stopping Rules**: `APPROVED`, `ESCALATE`, or `STOP` (`MAX_ATTEMPTS_EXCEEDED`, `UNSAFE_ACTION`, `NON_POSITIVE_EV`, `LOW_CONFIDENCE`).
  - **Evidence Rationale**: Evidence-based deterministic explanation text.
- Includes **"Execute Simulated Action"** button (invokes `POST /execute`) with simulation disclaimer.

### 4. Audit Trail View
- Searchable decision audit trail (`GET /audit/{decision_id}`).
- Renders complete action candidate evaluation matrix, safety clearance, predicted probabilities, EV values, selection status, and raw JSON snapshot viewer.

### 5. Evaluation Dashboard
- Summarizes Task 11 and Task 12 evaluation, model predictive metrics (held-out test ROC AUC 0.8600, Brier 0.1485), the direct ground-truth benchmark (regret ₹3.12/event), and Task 12 economic sensitivity & distribution shift robustness table.

---

## 4. How to Run Locally

### Step 1: Start Backend Service
```bash
# From workspace root: C:\Users\admin\Documents\Razorpay
uvicorn src.api.app:app --reload --port 8000
```

### Step 2: Start Frontend Application
```bash
# From frontend directory: C:\Users\admin\Documents\Razorpay\frontend
npm run dev
```
Open browser at `http://localhost:5173`.

---

## 5. 60–90 Second Reviewer Demo Flow

1. **Overview (15s)**: Open Overview. Show the +40.78% net economic gain (+₹681.80/event) and the Safety Gate comparison widget (0.00% vs 83.23% ablation).
2. **Payment Queue (15s)**: Open Payment Queue. Filter by `UPI Intent` or `Network Timeout`. Select payment episode `pay_evt_88840335` and click **"Analyze"**.
3. **Decision Inspector (25s)**: Click **"Analyze Recovery with O1"** (invokes `POST /decide`). Review recommended action `switch_method`, recovery probability `52.45%`, net expected value `₹276.17`, and evidence rationale. Click **"Execute Action"** (invokes `POST /execute`).
4. **Audit Trail (15s)**: Click **"Inspect Full Decision Audit Record"** (invokes `GET /audit/{id}`). Show full 5-action probability/EV matrix and immutable decision record.
5. **Evaluation (10s)**: Open Evaluation tab to view held-out test ROC AUC `0.8600` and oracle regret `₹3.12`.

---

## 6. Testing & Build Verification

- **Backend Unit Tests**: `47 / 47 PASSED` across 7 test suites.
- **Frontend Build**: TypeScript compiler (`tsc`) + Vite production build (`dist/index.html`, `dist/assets/index-Csj2dHxl.js`) passed with **0 errors**.

---

## 7. Data Tier Disclosure & Limitations

> [!IMPORTANT]
> **TIER C DISCLOSURE**: Recovery probabilities, expected economic values, and SNIPS policy metrics displayed on this dashboard are derived from the project's synthetic evaluation environment (Task 10–12). They do not represent measured Razorpay production performance or real customer behavior. The executor is a simulation and does NOT perform real money movement or Razorpay API calls.
