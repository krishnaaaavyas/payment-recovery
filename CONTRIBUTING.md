# CONTRIBUTING & CODE REVIEW GUIDE — O1 ADVISOR

## Project Scope
This repository houses **O1 — Payment Failure Economic Recovery Advisor** built for **Razorpay Track 03 — AI Revenue Recovery**.

---

## Experimental Setup & Integrity Guidelines

1. **Tier C Data Transparency**:
   - Production Razorpay transaction data is NOT stored or required.
   - Experiments operate strictly within a non-circular synthetic environment informed by public Razorpay API webhook schemas.
   - Never claim simulated recovery performance as production Razorpay uplift.

2. **Zero Feature Leakage Policy**:
   - Model input features must strictly derive from decision-time context variables $X$ and candidate action string $a$.
   - Post-action fields (`recovered`, `time_to_recovery_hours`, `recovered_gmv`, `action_cost`, `downside_penalty`, `friction_cost`) and oracle ground truth fields (`SYNTHETIC_ORACLE_ONLY_*`) are strictly forbidden as input features.

3. **Deterministic Safety Gate Pre-Filtering**:
   - Hard safety rules in `src/data/safety.py` MUST be evaluated before policy recommendation. The ML model cannot override hard safety constraints.

4. **Reproducibility**:
   - All random seeds are initialized to `42` in `configs/synthetic_config.yaml`.
   - Run unit test suites before submitting changes:
     ```bash
     python -m unittest tests/test_generator.py
     python -m unittest tests/test_anti_circularity.py
     python -m unittest tests/test_task11_policy.py
     ```
