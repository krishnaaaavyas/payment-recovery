# Task 16D — Shifted Safety Gate & Residual Claim Correction

> **Project**: O1 — Payment Failure Economic Recovery Advisor
> **Track**: Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery
> **Branch**: `audit/task16d-shifted-safety-fixes`
> **Parent**: `1f568b3` (docs: record Task 16B correction commit hash)
> **Input audit**: Task 16C — Independent Post-Correction Verification (verdict: NEEDS CORRECTION)
> **Date**: 2026-09-02

---

## 1. Executive summary

Task 16C verified that all Task 16A critical and major findings were genuinely fixed, but
blocked sign-off on two defects it discovered independently. This task corrects them.

**The primary defect (16C NEW-1)** was that the robustness evaluator determined the safe
action set by string-splitting the stored `safe_actions` column — a snapshot taken at
dataset-generation time — instead of evaluating the Safety Gate on the context actually being
scored. When a distribution shift mutated `failure_category`, the policy selected from a
**pre-shift** safe set, and the violation counter compared the selection against that **same
pre-shift** set, so it could never register a breach. Measured on the pre-16D code:
**2,281 of 15,000 rows stale** under `SHIFT_FAILURE_MIX`, of which **1,327 permitted
`update_information` where the shifted specification forbids it**, and **1,277 real safety
violations went unreported** while the JSON emitted `safety_violations: 0`.

The fix recomputes `evaluate_safety_gate(shifted_context)` for every shifted row. Because the
stored column and the recomputed gate agree on **all 100,000 unshifted rows**, the change is a
provable no-op everywhere except the two category-shifting scenarios — which is exactly what
regeneration showed.

**The secondary defect (16C NEW-3)** was that the retry cap is a numeric comparison, so `NaN`
silently bypassed it (every NaN comparison is `False`) and `str`/`None` raised `TypeError`.
The gate now fails closed on any malformed attempt count.

Three residual documentation claims were corrected from the authoritative JSON, including one
**false safety claim** in the README.

**Result: 98 tests pass (83 existing + 15 new), 156 subtests. Dataset, model and Task 11
results are byte-identical — this task did not touch the headline science.**

### One correction to the task brief

The brief specified the canonical `SHIFT_COMBINED` uplift as **+₹3,046.41**. That figure came
from the *buggy* run. Once the Safety Gate is correctly recomputed the authoritative value is
**+₹2,964.94** (`reports/task12_robustness.json` → `distribution_shifts.SHIFT_COMBINED.uplift_ci.mean`).
Per FIX 5 the documentation was written from the regenerated report, not from the brief.

---

## 2. Task 16C defect being corrected

| ID | Severity | Defect |
| :--- | :--- | :--- |
| **NEW-1** | MAJOR | Distribution-shift evaluation used the stale pre-shift `safe_actions`; safety violations under shift were structurally unmeasurable; EV/regret wrong on 2 of 4 shifts |
| **NEW-2** | MAJOR | `TASK_12_ROBUSTNESS.md` published `SHIFT_COMBINED` uplift as **+₹7.49** (the regret value duplicated into the uplift cell), contradicting both the JSON and the README |
| **NEW-3** | MINOR–MAJOR | Safety gate Rule 2 failed open on `NaN` retry count; raised `TypeError` on `str`/`None` |
| **NEW-4** | MINOR | `scripts/demo_full_stack.md:70` retained the superseded ₹0.94 regret |
| **NEW-6** | MINOR | `README.md:192` claimed "Zero safety violations … in all twelve" — unsupported |

---

## 3. Root cause

### 3.1 NEW-1 — stale safety set

`src/evaluation/robustness.py` (pre-16D, line 128):

```python
def get_precomputed_safety_and_baseline(df):
    safe_actions_list = [s.split("|") for s in df["safe_actions"].values]   # <-- snapshot
```

`run_distribution_shifts` built `df_shifted` by copying `df_test_obs` and mutating
`failure_category`, `error_source`, `error_step`, `failure_code`, `payment_method`,
`card_network`, `amount`, `order_value_tier` — but **never `safe_actions`**. It then called the
helper on `df_shifted`, which returned the carried-over pre-shift string.

`evaluate_safety_gate` depends on exactly two context fields: `failure_category` and
`retry_count_before_event`. Two of four scenarios mutate `failure_category`, so those two
scenarios evaluated a shifted context against an unshifted safety specification.

Two consequences, both structural:

1. **Selection** drew from the wrong candidate set.
2. **The violation counter was tautological** — `rec_act` was chosen *from* `safe_a` and then
   tested with `if rec_act not in safe_a`, so it could only ever be 0 regardless of the
   underlying specification.

The baseline branch compounded it by zipping the *shifted* `failure_category` with the
*stale* `safe_a`.

The `expired_card → soft_decline` shift flips eligibility in **both** directions, which is why
it is the sharpest probe: `expired_card` permits `update_information` and forbids retries;
`soft_decline` forbids `update_information` and permits retries.

### 3.2 NEW-3 — malformed retry count

`src/data/safety.py` (pre-16D):

```python
retry_count = context.get("retry_count_before_event", 0)
...
if retry_count >= 3:          # NaN >= 3 is False -> cap skipped entirely
```

Task 16B added a `isinstance(cat, str)` guard for `failure_category` but gave
`retry_count_before_event` no equivalent treatment, so the "fail-closed even if API validation
is bypassed" contract held for one input field and not the other.

---

## 4. Files modified

| File | Change |
| :--- | :--- |
| `src/evaluation/robustness.py` | `get_precomputed_safety_and_baseline` → **`compute_safety_and_baseline`**, now recomputing from `evaluate_safety_gate`; 5 call sites updated; `run_distribution_shifts` gains explicit `shifted_contexts` / `shifted_safe_actions`, refreshes the stale columns, asserts the used set equals the gate's verdict, and masks the oracle ceiling with the shifted set; new `safety_gate_recomputed_on_shifted_context` provenance flag |
| `src/data/safety.py` | New `_is_valid_retry_count()`; **Rule 2a** default-deny for malformed attempt counts (`HARD_SAFETY_INVALID_RETRY_COUNT`) ahead of the existing cap check (now Rule 2b) |
| `tests/test_task16d_shifted_safety.py` | **New** — 15 tests / 33 subtests |
| `reports/task12_robustness.json` | Regenerated |
| `reports/figures/task12/*.png` | Regenerated (5) |
| `README.md` | Shift table regenerated from JSON; false absolute safety claim replaced |
| `TASK_12_ROBUSTNESS.md` | Shift table regenerated from JSON; correction notice extended; key finding qualified |
| `scripts/demo_full_stack.md` | ₹0.94 → ₹3.12 regret |
| `TASK_16B_SCIENTIFIC_CORRECTIONS.md` | Forward-reference note on the now-superseded shift row (numbers left unaltered) |
| `TASK_16D_SAFETY_ROBUSTNESS_CORRECTION.md` | **New** — this report |

**Not modified:** dataset, model, `task11_*.json`, generator, API schemas, agent, executor,
frontend.

---

## 5. Safety-gate fix

```python
# ------------------------------------------------------------------
# SAFETY GATE IS RE-EVALUATED ON THE SHIFTED CONTEXT.
# ------------------------------------------------------------------
shifted_contexts = df_shifted.to_dict(orient="records")
shifted_safe_actions = [evaluate_safety_gate(ctx)[0] for ctx in shifted_contexts]
df_shifted["safe_actions"] = ["|".join(sa) for sa in shifted_safe_actions]
df_shifted["safety_constraints_applied"] = [
    "|".join(evaluate_safety_gate(ctx)[1]) for ctx in shifted_contexts
]

safe_actions_list, baseline_actions = compute_safety_and_baseline(df_shifted)
assert safe_actions_list == shifted_safe_actions, (
    "Safety set used for the shifted decision does not match "
    "evaluate_safety_gate(shifted_context)."
)

for i in range(N):
    safe_a = shifted_safe_actions[i]          # selection constrained to the shifted set
    ...
ora_best_arr = masked_oracle_best(ora_ev_matrix, shifted_safe_actions)   # oracle too
```

Three defence layers: the helper can no longer read the column at all; the shifted frame's
stale columns are refreshed so nothing downstream can pick them up; and an assertion fails the
run if the two ever diverge. The oracle ceiling is masked with the same shifted set, so policy
and oracle are constrained identically.

**Direct proof that the assertions discriminate** — same behavioural checks run against a
faithful reconstruction of the old helper, on 300 `expired_card` rows shifted to
`soft_decline`:

```
pre-shift  gate:  ['do_nothing', 'switch_method', 'update_information']
post-shift gate:  ['do_nothing', 'retry_later', 'retry_now', 'switch_method']
stale stored col: ['do_nothing', 'switch_method', 'update_information']

OLD implementation (reads stored safe_actions):
  shifted_safe_actions == evaluate_safety_gate(shifted_context) : FAIL
  differs from stale pre-shift snapshot                         : FAIL
  no update_information permitted on soft_decline               : FAIL (279 rows permit it)

NEW implementation (recomputes from shifted context):
  shifted_safe_actions == evaluate_safety_gate(shifted_context) : PASS
  differs from stale pre-shift snapshot                         : PASS
  no update_information permitted on soft_decline               : PASS
```

---

## 6. Retry-count hardening

Smallest principled fix, consistent with the existing architecture: Pydantic keeps its
`int, ge=0` constraint at the API edge; the **domain gate stops trusting the type**.

```python
def _is_valid_retry_count(value):
    if isinstance(value, str) or value is None:      return False
    try:    as_int = int(value)
    except (TypeError, ValueError, OverflowError):   return False   # None, NaN, +/-inf
    if as_int < 0:                                   return False
    return bool(as_int == value)                     # rejects 3.9; accepts 3.0 / np.int64(3)

# Rule 2a: DEFAULT DENY - malformed attempt count
if isinstance(retry_count, bool) or not _is_valid_retry_count(retry_count):
    return ["do_nothing"], ["HARD_SAFETY_INVALID_RETRY_COUNT"]
```

| Input | Result | Constraint |
| :--- | :--- | :--- |
| `0, 1, 2, np.int64(2), 2.0` | full safe set | — (normal evaluation preserved) |
| `3, 4, 99, np.int64(3), 3.0, 10^9` | `["do_nothing"]` | `HARD_SAFETY_RETRY_CAP_EXCEEDED` |
| **`NaN`** | **`["do_nothing"]`** | `HARD_SAFETY_INVALID_RETRY_COUNT` |
| `inf`, `-inf`, `None`, `"3"`, `"abc"`, `-1`, `-99`, `3.9`, `True`, `False`, `[3]`, `b"3"` | `["do_nothing"]` | `HARD_SAFETY_INVALID_RETRY_COUNT` |
| missing key (default 0) | full safe set | — |

Nothing raises. API layer: `-1`, `3.9`, `"abc"`, `None` → **HTTP 422**; `3` → HTTP 200 with
`MAX_ATTEMPTS_EXCEEDED`. Existing valid behaviour is unchanged.

`inf`/`-inf` were caught by the new tests during development — `int(float('inf'))` raises
`OverflowError`, which the first draft of the guard did not catch. Fixed before commit.

---

## 7. Regression tests added

`tests/test_task16d_shifted_safety.py` — **15 tests, 33 subtests**, all behavioural.

| Test | Requirement | Asserts |
| :--- | :--- | :--- |
| `test_A` | — | Recomputation == stored column on unshifted data (proves the no-op) |
| `test_B` | D | Poison the column with all 5 actions; helper must ignore it and return the gate's verdict |
| `test_C` | A | Mutating `failure_category` alone changes the returned set |
| `test_D` | A | Fixture guard: the shift genuinely flips eligibility both ways |
| `test_E` | **B** | `shifted_safe_actions == evaluate_safety_gate(shifted_context)` |
| `test_F` | **D** | Result differs from the stale snapshot; no `update_information` on `soft_decline` |
| `test_G` | **C** | argmax-EV selection ∈ `shifted_safe_actions` and ∈ gate verdict |
| `test_H` | — | End-to-end: every shift reports 0 violations *and* carries the provenance flag |
| `test_I`–`test_N` | FIX 3 | Valid counts, cap enforced, **NaN does not bypass**, 13 malformed types fail closed without raising, missing key safe, API 422s |
| `test_O` | **E** | Unshifted economic-sensitivity scenario unchanged and still matches canonical JSON |

`test_B`, `test_E`, `test_F`, `test_G` fail against the pre-16D implementation (§5).

---

## 8. Documentation corrections

All values written **programmatically from `reports/task12_robustness.json`**, not typed by hand.

| File | Before | After |
| :--- | :--- | :--- |
| `TASK_12_ROBUSTNESS.md` | `SHIFT_COMBINED` uplift **+₹7.49** | **+₹2,964.94** (whole shift table regenerated) |
| `README.md` | `SHIFT_COMBINED` uplift +₹3,046.41 | **+₹2,964.94** (whole shift table regenerated) |
| `README.md:192` | "Zero safety violations and zero per-event dominance violations in all twelve." | Replaced with a scoped statement (below) |
| `scripts/demo_full_stack.md:70` | "near-zero theoretical oracle regret (₹0.94/event)" | "near-zero direct-simulator oracle regret (**₹3.12/event**)" |
| `TASK_16B_SCIENTIFIC_CORRECTIONS.md` | shift row now superseded | Forward-reference note added; **its numbers left unaltered** |

The replacement for the false absolute claim deliberately does not substitute a new absolute:

> Every scenario above constrains the policy to `evaluate_safety_gate(context)` evaluated on
> the *perturbed* context, and each reports zero violations against that specification. This is
> a statement about the safety-gated policy under perturbation; it is not a claim that the
> system is violation-free in general. Two separate results say otherwise and are reported as
> they stand: the deliberately unconstrained ablation (A3) breaches the action constraints on
> 83.23% of episodes, and before Task 16D the distribution-shift scenarios measured violations
> against a stale pre-shift safe set, which hid 1,277 real breaches under `SHIFT_FAILURE_MIX`.

**Verification:** `₹7.49` appears nowhere outside the 16B historical before/after table (which
now carries the forward-reference); `₹0.94` appears only inside explicit before/after rows in
16B and in the two banner-marked historical audits; no absolute "zero safety violations"
claim remains. All 20 shift values appear verbatim in both `README.md` and
`TASK_12_ROBUSTNESS.md` and match the JSON exactly (programmatic check).

---

## 9. Regenerated artifacts

| Artifact | Regenerated | Command |
| :--- | :--- | :--- |
| `reports/task12_robustness.json` | **Yes** | `python scripts/run_robustness.py` |
| `reports/figures/task12/*.png` (5) | Yes | same |
| `reports/task11_policy_evaluation.json` | Re-run, **byte-identical** | `python scripts/evaluate_policy.py` |
| `data/synthetic/*` | Re-run into scratch, **byte-identical** | verified against `checksums.json` |
| `models/recovery_predictor.joblib` | Not affected | — |
| Frontend | No source change → no rebuild | dashboard reads `/reports/summary` live |

The dataset check matters because `safety.py` is imported by the generator: the new Rule 2a
could in principle have changed generation. It did not — all six SHA-256 digests are unchanged,
because the generator supplies clean `int` attempt counts.

---

## 10. Before / after robustness metrics

Straight from `reports/task12_robustness.json`.

| Scenario | Metric | Before (16B) | After (16D) |
| :--- | :--- | ---: | ---: |
| `SHIFT_TRANSACTION_VALUE` | all | *unchanged* | *unchanged* |
| `SHIFT_PAYMENT_METHOD_MIX` | all | *unchanged* | *unchanged* |
| **`SHIFT_FAILURE_MIX`** | O1 EV | 2,483.54 | **2,657.82** |
| | Baseline EV | 1,380.30 | **1,626.02** |
| | Oracle EV | 2,487.83 | **2,659.05** |
| | Uplift | 1,103.25 | **1,031.80** |
| | Regret | 4.29 | **1.23** |
| **`SHIFT_COMBINED`** | O1 EV | 6,461.10 | **6,859.09** |
| | Baseline EV | 3,414.69 | **3,894.14** |
| | Oracle EV | 6,468.59 | **6,861.53** |
| | Uplift | 3,046.41 | **2,964.94** |
| | Regret | 7.49 | **2.45** |

Unshifted families (`economic_sensitivity`, `ground_truth_robustness`, `ablation_study`,
`stress_testing`) are **identical** — confirmed by dict equality against the pre-16D JSON.

**Interpretation, stated plainly.** Correcting the gate moved results in **both** directions.
Absolute EVs rose because the shifted `soft_decline` set permits retries the stale
`expired_card` set forbade, so all three policies get better options. But **uplift over
baseline fell** in both scenarios (−₹71.45 and −₹81.47), because the baseline benefits too.
Regret fell sharply (4.29 → 1.23; 7.49 → 2.45) because the policy is no longer forced into a
mismatched action set. The headline uplift is therefore slightly *less* favourable than
previously published, and that is reported as found.

---

## 11. Full test-suite result

```
python -m pytest tests/ -q
98 passed, 156 subtests passed in 64.99s
```

| Suite | Tests |
| :--- | ---: |
| Existing 8 suites (16A/16B baseline) | 83 |
| **`test_task16d_shifted_safety.py`** (new) | **15** |
| **Total** | **98** |

No existing test was removed, skipped, weakened or rewritten. `python scripts/demo_agent.py`
completes with zero safety violations.

---

## 12. Scientific integrity statement

This task did **not**:

- change the hidden oracle, model labels, or train/test boundaries — dataset, model and
  `task11_policy_evaluation.json` are byte-identical;
- introduce outcome leakage or use oracle fields in prediction — `compute_safety_and_baseline`
  reads only `failure_category` and `retry_count_before_event`, both pre-decision;
- tune the policy against test outcomes — the policy is unchanged; only the constraint set it
  is evaluated under was corrected;
- remove unfavourable results — the corrected uplift is **lower** in both affected scenarios
  and is published as such;
- suppress safety violations — the opposite: the previous `0` was structurally unmeasurable,
  and the 1,277 breaches it concealed are now documented in the README, `TASK_12` and here;
- alter denominators to improve metrics — all scenarios remain N = 15,000;
- manufacture documentation values — every published number was written programmatically from
  the regenerated JSON, including the one that contradicts the task brief (§1).

---

## 13. Git commit

```
Commit:  9bef215f4ef68e702d82e301626710e7ade58885 (short: 9bef215)
Branch:  audit/task16d-shifted-safety-fixes
Message: fix: correct shifted safety evaluation and residual claims
```

One commit. Nothing pushed, no remote configured, `main` untouched, history not rewritten.

---

## 14. Working tree status

```
On branch audit/task16d-shifted-safety-fixes
nothing to commit, working tree clean
```

---

## 15. Remaining limitations

Carried forward from Task 16C and **not** addressed here (out of scope for a surgical fix):

1. **NEW-7** — `AuditStore.get_audit()` returns a live mutable reference; a caller can mutate a
   stored audit record in place. Not disclosed in 16B's limitations.
2. **NEW-8** — `predict_proba` accepts arbitrary action strings, silently scored as an all-zero
   one-hot; no action-space guard at the model layer.
3. **NEW-5** — `TASK_13A_BACKEND.md:10` still says "production-grade" while the API has no
   authentication on any endpoint.
4. **NEW-9** — A1 (max probability) ₹2,353.58 ≥ A2 (max EV) ₹2,353.54: the economics layer
   contributes −₹0.04/event, so "economic optimization" is not demonstrably additive here.
5. **NEW-10** — the agent returns `status=APPROVED` for an unrecognized category (safe
   `do_nothing`) rather than signalling invalid input.
6. **16A N-9** — a `NON_POSITIVE_EV`/`UNSAFE_ACTION` stop emits `do_nothing` but records
   `safe=False`.
7. **16A N-4/N-5/N-6** — dead `bootstrap_resamples` config key; `compute_bootstrap_ci` uses a
   fixed seed so CIs are correlated across scenarios; probabilities rounded to 4dp.
8. **Structural** — regret remains a small difference of large numbers and is sensitive to the
   data draw; the evaluated policy still omits the deployed agent's stopping rules (4.45%
   would escalate); the baseline remains close to the data-generating heuristic; the
   "temporal" split carries no temporal structure.
9. **Not re-audited here** — figure PNGs have no programmatic provenance check.

---

## 16. Readiness for Task 16E

The two Task 16C blocking defects (NEW-1, NEW-2) and the three residual claim defects (NEW-3,
NEW-4, NEW-6) are corrected, covered by 15 new behavioural regression tests, and verified
against regenerated artifacts. The full suite passes at 98 tests / 156 subtests, the dataset
and Task 11 results are provably untouched, and the working tree is clean at a single commit.

**This branch is ready for an independent Task 16E re-audit.**

A 16E auditor should prioritise: (a) re-deriving the shifted safe sets independently for all
four scenarios; (b) confirming the uplift *decrease* is genuine and not a masking artifact;
(c) the limitations in §15, none of which this task claims to have fixed.

> [!IMPORTANT]
> **TIER C DISCLOSURE.** Every figure here comes from the project's synthetic evaluation
> environment. In our synthetic evaluation environment these are the measured results; they are
> **not** Razorpay production performance, real customer recovery probabilities, or real money
> movement.
