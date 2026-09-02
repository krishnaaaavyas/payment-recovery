# Task 16B — Scientific Corrections & Evaluation Integrity Fix

> **Project**: O1 — Payment Failure Economic Recovery Advisor
> **Track**: Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery
> **Branch**: `audit/task16b-scientific-corrections`
> **Parent checkpoint**: `156a4cc` (audit: verify clean environment reproduction)
> **Input audit**: [`docs/audits/TASK_16A_INDEPENDENT_SCIENTIFIC_AUDIT.md`](docs/audits/TASK_16A_INDEPENDENT_SCIENTIFIC_AUDIT.md)
> **Date**: 2026-09-02

---

## 1. Executive summary

The Task 16A independent audit returned a verdict of **NEEDS CORRECTION** against commit
`156a4cc`, citing 3 critical and 7 major findings. This task investigated each finding
against the source, fixed the confirmed root causes in the implementation, regenerated every
downstream artifact from the corrected code, and reconciled all submission-facing
documentation and dashboard values against the regenerated artifacts.

**All 3 critical and all 7 major findings were confirmed and corrected.** One finding the
audit reported (`is_subscription` int/bool mismatch, N-1 adjacent) turned out **not** to be a
real defect and is documented as not-reproducible with evidence. One **new** defect was
discovered by the regression tests written for this task and fixed.

Nothing was fixed by editing a number. Every metric in this report and in the updated
documentation was produced by re-running the corrected pipeline.

### What changed materially

| | Before (`156a4cc`) | After (this task) |
| :--- | ---: | ---: |
| Test events with no matching oracle row | **114** | **0** |
| Oracle join row count (expected 15,000) | **15,015** | **15,000** |
| Episodes scored in A3 ablation | **2,368 (15.8%)** | **15,000 (100%)** |
| Distribution shifts scored against correct ground truth | **No** | **Yes** |
| `ranking_stable` emitted | **`false`** (NaN artifact) | **`true`** (genuinely computed) |
| "Ground-Truth Robustness" experiment | **Described, not implemented** | **Implemented, 3 scenarios** |
| Safety gate on unknown category | **Fails open — all 5 actions** | **Fails closed — `do_nothing`** |
| Executor replay of one decision | **Permitted, unbounded** | **Rejected after first execution** |
| Executor `payment_id` binding | **Never checked** | **Enforced** |
| Headline model metric | **Validation, labelled "test"** | **Held-out test, labelled as such** |
| SNIPS reported with uncertainty | **No** | **Yes — 95% bootstrap CI + ESS** |
| Dashboard metric source | **Hardcoded constants** | **Live `GET /reports/summary`** |
| Test count | **53** | **83** (+123 subtests) |

### Headline metric movement

The corrected authoritative figure is the **direct ground-truth simulator benchmark**, not
SNIPS. The previously headlined SNIPS uplift has been demoted to a supporting estimator.

| Metric | Before | After | Why it moved |
| :--- | ---: | ---: | :--- |
| Headline uplift | +₹879.32 (+56.8%), SNIPS | **+₹681.80 (+40.78%), direct** | Headline switched from a 37.8%-coverage estimator to the full-population ground truth |
| Regret vs oracle | ₹0.94 | **₹3.12** | Previous value was a difference of means over mismatched populations; also a new model on a regenerated dataset |
| Policy efficiency | 99.96% | **99.87%** | Same |
| Model ROC AUC | 0.8532 (validation) | **0.8600 (held-out test)** | Split correctly labelled; test metrics now computed |
| Model Brier | 0.1516 (validation) | **0.1485 (held-out test)** | Same |
| A3 no-safety-gate EV | ₹2,984.68 | **₹2,454.54** | Denominator corrected from 15.8% to 100% of episodes |
| A3 violation rate | 84.21% | **83.23%** | Recomputed on the regenerated dataset with the retrained model |

---

## 2. Audit findings addressed

| # | Finding | Status |
| :--- | :--- | :--- |
| C-1 | Oracle / event-id misalignment corrupts ground-truth figures | **CONFIRMED → FIXED** |
| C-2 | Safety Gate fails open on unrecognized `failure_category` | **CONFIRMED → FIXED** |
| C-3a | Fabricated O1 action distribution in docs and dashboard | **CONFIRMED → FIXED** |
| C-3b | README/dashboard robustness matrix matches no committed run | **CONFIRMED → FIXED** |
| C-3c | "Ground-Truth Robustness" experiment never implemented | **CONFIRMED → IMPLEMENTED** |
| C-3d | "STABLE" asserted while report says `ranking_stable: false` | **CONFIRMED → FIXED (root cause)** |
| M-1 | A3 ablation EV is a `nanmean` over 15.8% of events | **CONFIRMED → FIXED** |
| M-2 | Distribution shifts scored against unshifted ground truth | **CONFIRMED → FIXED** |
| M-3 | SNIPS headlined without uncertainty | **CONFIRMED → FIXED** |
| M-4 | Validation metrics labelled as test metrics | **CONFIRMED → FIXED** |
| M-5 | Executor replay + no `payment_id` binding | **CONFIRMED → FIXED** |
| M-6 | Evaluated policy ≠ deployed policy | **CONFIRMED → DOCUMENTED** (see §16) |
| M-7 | Baseline ≈ data-generating policy | **CONFIRMED → DOCUMENTED** (see §16) |
| N-1 | API schema defaults outside training vocabulary | **CONFIRMED → FIXED** |
| N-1b | `is_subscription` int vs bool mismatch | **NOT REPRODUCIBLE** (see §3.11) |
| — | Defaulted enum fields leak `Enum` members (new) | **DISCOVERED → FIXED** |
| N-4, N-8, N-10 | Dead config key, dashboard render bug, unpinned deps | **CONFIRMED → FIXED** |

---

## 3. Root cause and correction, finding by finding

### 3.1 C-1 — Oracle / event-id misalignment

**Root cause.** Three compounding defects, not one:

1. `src/data/generate_synthetic.py:94` drew `event_id` **with replacement** from a
   90 M-wide integer range. At N = 100,000 this produced 57 collisions.
2. The oracle frame was then realigned by **label**:
   `df_oracle.set_index("event_id").loc[df_obs["event_id"]]`. With a duplicated label,
   `.loc` returns every matching row for every requested occurrence, so the oracle frame
   grew *longer* than the observed frame.
3. `save_and_split_dataset` sliced **both** frames with boundaries computed from
   `len(df_obs)`. Because the oracle frame was longer, every split boundary landed on a
   different episode in each frame, and the tail was truncated.

The measured consequence on the test split was 114 test events with no oracle row, 103 rows
belonging to *validation* events, and an un-validated `merge` that produced 15,015 rows.

**Correction.** All three layers, so no single failure can silently reintroduce it:

- Identifiers are now sequential and collision-free by construction
  (`evt_00000000`…`evt_00099999`). They are not model features.
- Reordering uses a **positional permutation** applied to both frames
  (`np.argsort(..., kind="stable")`), which cannot expand rows regardless of label
  uniqueness.
- A new `_assert_observed_oracle_alignment()` asserts row-count equality, uniqueness in
  both frames, exact positional `event_id` equality, and set equality — invoked after
  generation, before splitting, and again per split with the expected split size.
- `src/policy/evaluation.py` now joins with `how="inner", validate="one_to_one"`, asserts
  the post-merge row count equals N, and asserts no NaN survives into any mean.
- `src/evaluation/robustness.py` no longer papers over duplicates with
  `drop_duplicates()`; it asserts uniqueness and validates the join.

**Note on the previous `drop_duplicates()` workaround.** Task 12 already contained it at
four call sites. That is why Task 12 reported regret ₹1.56 while Task 11 reported ₹0.94 for
the same experiment. The workaround suppressed the symptom in one code path while the root
cause remained. It has been removed in favour of the assertions.

**Verification.**

```
train  obs=70000 ora=70000 unique=True positional_aligned=True set_equal=True
val    obs=15000 ora=15000 unique=True positional_aligned=True set_equal=True
test   obs=15000 ora=15000 unique=True positional_aligned=True set_equal=True
TOTAL  obs=100000 ora=100000 global_unique_event_id=True duplicates=0
test merge rows=15000 (expected 15000)   NaN oracle best_ev = 0
```

`tests/test_task11_policy.py::test_13_oracle_join_rejects_misaligned_frames` feeds a
deliberately duplicated oracle frame and asserts the evaluation now raises rather than
silently inflating the population.

---

### 3.2 C-2 — Safety Gate fail-open

**Root cause.** `evaluate_safety_gate` was a **deny-list with no terminal branch**. It
matched `failure_category` against hard-coded lists; anything that matched none of them fell
through to `safe = set(ALL_ACTIONS)` with an empty constraint list. `FailedPaymentEvent`
applied no enum constraint, so any string reached the gate. `OneHotEncoder(handle_unknown="ignore")`
then encoded the unknown value as an all-zero block, so the model still returned a confident
probability.

**Correction — defence in depth, three independent layers:**

1. **Domain layer (authoritative).** A new **Rule 0** in `src/data/safety.py`:
   ```python
   if not isinstance(cat, str) or cat not in SUPPORTED_FAILURE_CATEGORIES:
       return ["do_nothing"], ["HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY"]
   ```
   `SUPPORTED_FAILURE_CATEGORIES` is derived from `FAILURE_TAXONOMY`, so the gate and the
   taxonomy cannot drift. The `isinstance` guard means non-string input (`None`, numbers,
   lists) fails closed instead of raising on the membership test.
2. **API layer.** Every categorical field is now a closed `str`-valued `Enum` sourced from a
   single vocabulary in `src/data/failure_taxonomy.py`. Unknown values are rejected with
   **HTTP 422** before reaching the model.
3. **No normalization on purpose.** `"HARD_DECLINE"` and `" hard_decline "` are *blocked*,
   not silently coerced to `hard_decline`. Coercion would mask an upstream integration fault.

**Deliberate design note.** The gate is fail-closed but not normalizing, so a genuinely
mis-cased upstream feed will see rejections rather than silent misclassification. That is the
intended trade-off for a safety boundary.

**Verification.** Live probes against `POST /decide`:

| Input `failure_category` | Before | After |
| :--- | :--- | :--- |
| `"hard_decline"` | `do_nothing`, rule applied | `do_nothing`, rule applied (unchanged) |
| `"HARD_DECLINE"` | **`update_information`, APPROVED, no rule** | **HTTP 422** |
| `" hard_decline "` | **`update_information`, APPROVED, no rule** | **HTTP 422** |
| `"chargeback_fraud_confirmed"` | **`update_information`, APPROVED, no rule** | **HTTP 422** |
| Same, with API validation bypassed | **`update_information`** | **`do_nothing` + `HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY`** |

---

### 3.3 C-3a/b — Untraceable published figures

**Root cause.** Documentation and dashboard restated metrics as literal constants rather than
reading them from the generated artifacts, so they drifted from `reports/*.json` with nothing
to detect it. `GET /reports/summary` and `fetchEvaluationReports()` both existed and neither
was ever called.

**Correction.**
- `Evaluation.tsx` and `Overview.tsx` now fetch `GET /reports/summary` and render from it.
  No evaluation metric is a literal in the frontend any more; `ACTION_META` carries only
  labels and colours, with percentages coming from the artifact.
- `/reports/summary` additionally serves `task11_model_results.json` so model metrics are
  sourced the same way.
- `frontend/src/types/api.ts` `EvaluationSummary` was rewritten — the previous type described
  keys (`evaluation_b_off_policy`, `evaluation_c_oracle_benchmark`) that never existed in any
  emitted JSON.
- All Markdown tables were regenerated from the corrected artifacts.
- Fixed the render bug at the old `Evaluation.tsx:167` where a stray class name displayed
  literally as `₹1,656.32 font-mono`.

---

### 3.4 C-3c — "Ground-Truth Robustness" experiment implemented

**Root cause.** `configs/robustness_config.yaml` defined a `ground_truth_robustness` block
with `interaction_scale` values, `TASK_12_ROBUSTNESS.md §4` reported regret figures of ₹1.12
and ₹2.05 for it, but **no code read the key**, the runner had no such phase, the results JSON
had no such key, and `compute_true_recovery_probability` was imported into `robustness.py` and
never called.

**Correction — implemented rather than deleted**, because the experiment is scientifically
valuable: it is the one test that asks whether O1's advantage is an artifact of one particular
simulator parameterization.

- `compute_true_recovery_probability` gained an `interaction_scale: float = 1.0` parameter
  that scales the five hidden interaction terms **as a group**, leaving the base action logit,
  category effect, retry decay and history signal untouched.
- `run_ground_truth_robustness()` re-scores the **frozen** policy (no retraining) under each
  scale and is wired into `scripts/run_robustness.py` as phase 5.

**The default is provably a no-op:** regenerating the full dataset after the refactor produced
byte-identical SHA-256 digests for all six CSVs.

**Result — these are the real numbers, and they differ from the figures previously claimed:**

| Scenario | Scale | O1 EV | Baseline EV | Oracle EV | Uplift | Regret |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: |
| STANDARD | 1.0× | ₹2,353.54 | ₹1,671.74 | ₹2,356.66 | +₹681.80 | ₹3.12 |
| WEAKER_CONTEXTUAL_INTERACTIONS | 0.5× | ₹2,066.47 | ₹1,565.17 | ₹2,069.58 | +₹501.30 | ₹3.12 |
| STRONGER_CONTEXTUAL_INTERACTIONS | 1.5× | ₹2,481.09 | ₹1,678.18 | ₹2,483.44 | +₹802.91 | ₹2.35 |

O1's advantage shrinks when the structure it learned is halved and grows when amplified,
while regret stays near zero throughout.

---

### 3.5 C-3d — `ranking_stable` always false

**Root cause.** `robustness.py:170` used `np.mean` (not `nanmean`) on arrays containing the
114 NaNs introduced by C-1. `np.mean` of an array containing NaN returns NaN, and every
comparison against NaN is `False`. The adjacent CI fields used `nanmean`, which is why the
inconsistency was not visually obvious in the JSON.

**Correction.** Fixing C-1 removed the NaNs at source; the comparison was additionally made
explicit with `float(...)` casts, and `ranking_stable` is now emitted for distribution shifts
and ground-truth scenarios too. It is now genuinely `true` in all 13 scenarios — and the
documentation states that it is read from the field, not asserted in prose.

---

### 3.6 M-1 — A3 ablation denominator

**Root cause.** The oracle CSV stores `NaN` for any action outside the safe set at generation
time. A3 deliberately ignores the safety gate, so it selected forbidden actions on ~84% of
episodes; `np.nanmean` silently dropped every one of those rows. A3's published ₹2,984.68 was
the mean over the **2,368 episodes (15.8%)** where its unconstrained choice happened to be
legal — a survivorship-selected subset printed in the same column as variants scored on all
15,000.

**Correction.** New `compute_true_ev_matrix()` computes ground truth for **every action on
every row** directly from the simulator, so no cell is NaN. An assertion fails the run if any
appears. Every ablation row now reports `events_in_population`, `events_evaluated` and
`events_missing_ground_truth` explicitly.

**Result — and the finding it changes.**

| Variant | Before | After | Episodes scored | Violations |
| :--- | ---: | ---: | ---: | ---: |
| A0 Rule baseline | ₹1,668.91 | ₹1,671.74 | 15,000 | 0 (0.00%) |
| A1 Predictive only | ₹2,349.03 | ₹2,353.58 | 15,000 | 0 (0.00%) |
| A2 ML + economics | ₹2,349.06 | ₹2,353.54 | 15,000 | 0 (0.00%) |
| **A3 no safety gate** | **₹2,984.68 (15.8%)** | **₹2,454.54 (100%)** | 15,000 | 12,485 (83.23%) |
| A4 Full architecture | ₹2,349.06 | ₹2,353.54 | 15,000 | 0 (0.00%) |

**A3 still scores higher than the gated architecture (₹2,454.54 vs ₹2,353.54), and we now say
so explicitly.** In this synthetic environment the Safety Gate *costs* about ₹101/event: the
modelled ₹5.00 misalignment penalty is far too small to offset the simulator's +0.2 base logit
for `update_information`. The gate is a compliance boundary imposed from outside the economic
model, not a free optimization. The previous framing — that the ablation "proves the Safety
Gate is indispensable" on EV grounds — was not supportable, and the mechanism was also
mis-described: it is **action-space extrapolation** (a positivity violation), because
`update_information` is only ever logged where the gate permits it.

---

### 3.7 M-2 — Distribution shifts vs stale ground truth

**Root cause.** `run_distribution_shifts` mutated `failure_category`, `payment_method` and
`amount` in the model's input frame, then read `SYNTHETIC_ORACLE_ONLY_true_p_{a}` from the
**original** oracle CSV. The simulator's hidden interactions depend on exactly those fields,
so the policy was scored in one world against the truth of another. The same defect affected
economic sensitivity, where `value_multiplier` scaled `amount` without recomputing the
amount-dependent interaction.

**Correction.** Both now call `compute_true_ev_matrix()` on the perturbed contexts.
Additionally, taxonomy-derived fields are updated consistently with the shift so the model is
never fed a self-contradictory context vector:

| Shifted field | Derived fields now updated |
| :--- | :--- |
| `failure_category` → `soft_decline` | `error_source`, `error_step`, `failure_code` |
| `amount` × multiplier | `order_value_tier` |
| `payment_method` → `upi_intent` | `card_network` → `none` |

**Result.**

| Shift | Before (stale GT) | After (recomputed GT) | Regret before → after |
| :--- | ---: | ---: | ---: |
| Transaction value 3.0× | ₹7,078.57 | ₹7,516.64 | ₹4.18 → ₹5.08 |
| Failure mix 60% soft | ₹2,349.65 | ₹2,483.54 | ₹1.39 → ₹4.29 |
| Payment mix 70% UPI | ₹2,349.90 | ₹2,359.09 | ₹1.54 → ₹2.96 |
| Combined | ₹5,896.19 | ₹6,461.10 | ₹3.39 → ₹7.49 |

The qualitative conclusion survives — regret stays small and the ranking holds — but the
published numbers were wrong by up to ₹309/event under the old method, and the claim of
"zero degradation" has been replaced with the accurate reading: the oracle ceiling itself
moves with the shift, and O1 stays close to it in the shifted world.

---

### 3.8 M-3 — SNIPS interpretation

**Root cause.** The `+₹879.32 / +56.8%` headline was a difference of two SNIPS point
estimates from a 38.5%-coverage estimator with ESS 1,730 (11.5% of N), published with no
uncertainty anywhere in the repository.

**Correction.** SNIPS is **kept** — off-policy evaluation is the deployment-relevant method —
but demoted from headline to supporting evidence, and reported honestly:

- New `bootstrap_snips_ci()` (2,000 replicates, seed 0) resamples **events**, not matched
  events, so the interval reflects both which episodes land in the sample and which the
  logging policy matched.
- The report JSON now separates `direct_ground_truth_benchmark` (labelled
  `role: AUTHORITATIVE`) from `off_policy_snips_evaluation` (labelled
  `role: Off-policy estimator … NOT ground truth`), each carrying an `interpretation` string.
- Overlap diagnostics are emitted: min propensity, max importance weight, clipping flag,
  matched events, ESS and ESS fraction.
- `snips_minus_direct_true_ev_inr` is emitted and explicitly described as estimator variance.

**Investigation of the SNIPS/direct discrepancy — not forced to match.** SNIPS reads ₹2,415.74
against the direct value of ₹2,353.54, a gap of **+₹62.20**. The bootstrap standard error is
**₹201.53**, so the gap is **0.31 standard errors** — ordinary sampling noise on an
11.5%-ESS estimator over heavy-tailed lognormal rewards. Overlap is genuine (min propensity
0.075, max weight 13.33, zero unsupported target actions), so the estimator is not biased by
support violations. No clipping was applied and none is needed. The two estimates are
consistent; they have not been reconciled by adjustment.

---

### 3.9 M-4 — Validation vs test metrics

**Root cause.** `train_recovery_model.py` scored six candidates on `val.csv`, selected the
minimum-Brier candidate on `val.csv`, and wrote those same validation metrics to the report.
`TASK_11_RESULTS.md §5` then printed them under the heading "Evaluation Results (Test Set:
15,000 Events)". No test-set metric was computed anywhere in the pipeline.

**Correction.** The test split is now scored **once**, after selection is frozen, and the
report JSON carries `train_metrics`, `validation_metrics` and `test_metrics` as separate keys
plus a `note` field explaining that validation figures are optimistically biased. The
chronological split is unchanged; validation is never reused as test.

| Split | ROC AUC | Brier | Log loss | Cal. error | Role |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Train | 0.8626 | 0.1474 | 0.4317 | 0.0214 | — |
| Validation | 0.8584 | 0.1494 | 0.4384 | 0.0166 | **Model selection** (biased) |
| **Test** | **0.8600** | **0.1485** | **0.4344** | **0.0085** | **Headline (held out)** |

---

### 3.10 M-5 — Executor replay and payment binding

**Root cause.** `payment_id` was accepted as a parameter and used only to populate the
response; it was never compared with `audit_record["payment_id"]`. And although
`update_execution_status` was called after a successful execution, nothing read it back, so
one approval could dispatch unbounded executions.

**Correction** (checks 2 and 3, before the existing action/status/safety checks):

- **Payment binding** — request `payment_id` must equal the decision's `payment_id`.
- **Replay rejection** — a decision whose `execution_status != "pending"` is rejected. A
  rejected-for-mismatch attempt deliberately leaves the record `pending` so the rightful
  owner can still execute.

Scope was kept to decision integrity; no authentication was added, because the executor
remains simulation-only and adding auth would be production functionality beyond this task.
That gap is recorded in §16.

**Verification.**

| Probe | Before | After |
| :--- | :--- | :--- |
| Execute same approved decision 3× | 3 × HTTP 200 | 1 × 200, then **HTTP 400 rejected** |
| Execute under a foreign `payment_id` | HTTP 200 `scheduled` | **HTTP 400 rejected** |

---

### 3.11 NOT REPRODUCIBLE — `is_subscription` int vs bool

The audit's N-1 area suggested the API's `is_subscription: int` (0/1) mismatches the training
data's `bool` dtype. **This is not a real defect**, and evidence is recorded rather than a
change being made:

```
training dtype: bool     encoder categories: [False  True]
API value:      0 (int)
prediction with bool False : 0.273
prediction with int   0     : 0.273   <- identical
```

`OneHotEncoder` on an object-dtype column resolves categories by hash/equality, and
`hash(0) == hash(False)` with `0 == False`, so the lookup succeeds. A first draft of the new
regression test asserted string-equality against the CSV vocabulary and **failed on this
field** — a false positive. The test was corrected to assert the property that actually
matters (the one-hot block for each categorical column must be non-zero after transformation,
i.e. the encoder recognized the value), which is strictly stronger than string matching and
does not produce this false positive.

---

### 3.12 NEW DEFECT — defaulted enum fields leaked `Enum` members

**Discovered by** `test_schema_defaults_are_recognized_by_the_fitted_encoder`, written for
this task.

Pydantic v2 does not validate defaults unless `validate_default=True`. With only
`use_enum_values=True`, fields the caller **supplied** were converted to plain strings while
fields left at their **default** retained the `Enum` member — so `str(ctx["currency"])`
rendered as `"CurrencyEnum.INR"`, which would land in the audit record and the feature vector.

**Correction.** `model_config = ConfigDict(use_enum_values=True, validate_default=True)`, plus
a dedicated regression test asserting every categorical field of a defaulted event
`is` a plain `str`.

---

## 4. Exact implementation changes

| File | Change |
| :--- | :--- |
| `src/data/generate_synthetic.py` | Sequential collision-free `event_id`/`order_id`; positional (not label-based) reordering of both frames; new `_assert_observed_oracle_alignment()` invoked after generation, before split, and per split; vocabulary constants imported from `failure_taxonomy` |
| `src/data/failure_taxonomy.py` | Added closed context vocabularies (`PAYMENT_METHODS`, `CORRIDORS`, `FAILURE_CODES`, …) as the single source of truth shared by generator, API schema and safety gate |
| `src/data/safety.py` | **Rule 0 default-deny** for unrecognized/non-string `failure_category`; `SUPPORTED_FAILURE_CATEGORIES` derived from the taxonomy |
| `src/data/ground_truth.py` | `interaction_scale` parameter scaling the five hidden interaction terms as a group; default 1.0 verified byte-identical |
| `src/api/schemas.py` | 13 categorical fields constrained to closed `str`-Enums; in-vocabulary defaults; `validate_default=True` |
| `src/api/app.py` | `/reports/summary` also serves `task11_model_results.json`; loader refactored |
| `src/agent/executor.py` | Payment-id binding check; replay rejection; checks renumbered |
| `src/policy/evaluation.py` | `validate="one_to_one"` join + population assertions; per-event dominance assertion; no-NaN assertions; `bootstrap_snips_ci()`; report restructured into `direct_ground_truth_benchmark` (authoritative) and `off_policy_snips_evaluation` (estimator) with overlap diagnostics |
| `src/evaluation/robustness.py` | New `compute_true_ev_matrix()` and `masked_oracle_best()`; ablation/shifts/sensitivity/stress all recompute ground truth from the simulator; explicit denominators; `drop_duplicates` workarounds replaced with validated joins; new `run_ground_truth_robustness()` |
| `scripts/train_recovery_model.py` | Held-out test scoring after selection; train/validation/test metrics reported separately with a bias note |
| `scripts/evaluate_policy.py` | Summary output and figures updated for the restructured report; direct benchmark labelled authoritative |
| `scripts/run_robustness.py` | Phase 5 (ground-truth robustness) wired in |
| `frontend/src/components/Evaluation.tsx` | Rewritten to fetch `GET /reports/summary`; renders direct benchmark, SNIPS with CIs, ablation with denominators, 13-scenario robustness matrix; loading/error states |
| `frontend/src/components/Overview.tsx` | Headline metrics, safety comparison and action distribution now live from the artifact; render bug fixed |
| `frontend/src/types/api.ts` | `EvaluationSummary` rewritten to match the artifacts actually emitted |
| `tests/test_task16b_safety_regression.py` | **New** — 27 tests / 123 subtests covering safety, API validation, agent-level fail-closed, executor binding and replay |
| `tests/test_task11_policy.py` | Updated for restructured report; 4 new tests (overlap diagnostics, full-population coverage, per-event dominance, misaligned-join rejection) |
| `requirements.txt`, `requirements-lock.txt` | Upper bounds + exact verified pins; model/sklearn coupling documented |
| `README.md`, `TASK_11`, `TASK_12`, `TASK_13B`, `TASK_14`, `TASK_15`, `docs/*`, `DATASET_CARD.md`, `scripts/demo_full_stack.md` | Reconciled with regenerated artifacts; correction notices added |
| `TASK_16_REPRODUCTION_AUDIT.md`, `docs/audits/TASK_16A_*.md` | Superseded banners; **numbers left unaltered** as historical evidence |

---

## 5. Before / after metrics

Authoritative source: `reports/task11_model_results.json`, `reports/task11_policy_evaluation.json`,
`reports/task12_robustness.json` — all regenerated from the corrected code.

| Metric | Before (`156a4cc`) | After | Note |
| :--- | ---: | ---: | :--- |
| Direct true O1 policy EV | ₹2,349.72 | **₹2,353.54** | Full population, correctly joined |
| Direct true oracle best EV | ₹2,350.67 | **₹2,356.66** | |
| Direct true baseline EV | ₹1,668.04 | **₹1,671.74** | |
| Direct regret | ₹0.94 | **₹3.12** | Previously a difference over mismatched populations |
| Policy efficiency | 99.96% | **99.87%** | |
| Direct uplift | not reported | **+₹681.80 (+40.78%)** | New headline |
| Per-event dominance violations | not computed | **0 / 15,000** | Now asserted |
| Action matches oracle-best | not reported | **96.85%** | |
| SNIPS O1 EV | ₹2,425.91 | ₹2,415.74 | 95% CI ₹2,088.89–₹2,861.67 |
| SNIPS baseline EV | ₹1,546.59 | ₹1,676.60 | 95% CI ₹1,567.68–₹1,785.87 |
| SNIPS ESS | 1,730.5 | 1,724.6 | 11.5% of N |
| Model ROC AUC | 0.8532 (val) | **0.8600 (test)** | |
| Model Brier | 0.1516 (val) | **0.1485 (test)** | |
| Safety violation rate | 0.00% | **0.00%** | Unchanged |
| A3 EV / violations | ₹2,984.68 / 84.21% | **₹2,454.54 / 83.23%** | Denominator corrected |
| Tests | 53 | **83** (+123 subtests) | |

**Why the direct EVs moved by only a few rupees while regret nearly tripled.** The context
features are drawn before the identifiers in the RNG stream, so the corrected generator
produces **identical contexts** — the oracle ceiling (₹2,356.66) and baseline (₹1,671.74)
match the audit's independent recomputation on the old data exactly. What changed downstream
of the id fix is the failure codes, logged actions and sampled outcomes, hence a slightly
different trained model and a slightly different policy. Regret is a small difference of two
large numbers (₹3.12 against ₹2,356.66, i.e. 0.13%), so it is the most sensitive quantity in
the report and moves visibly with an ordinary re-draw. This is itself a finding, recorded in
§16.

---

## 6. Direct simulator evaluation (authoritative)

```
Episodes evaluated:               15,000 / 15,000   (missing ground truth: 0)
Direct true baseline policy EV:   INR 1,671.74 / event
Direct true O1 policy EV:         INR 2,353.54 / event
Direct true oracle best EV:       INR 2,356.66 / event
Direct true regret:               INR 3.1197 / event
Direct policy efficiency:         99.8676%
Direct uplift over baseline:      INR 681.80 / event  (+40.78%)
Per-event dominance violations:   0
Per-event regret min / max:       0.000000 / 1,025.20
Action matches oracle-best:       96.85%
```

The oracle is defined as `max EV_true(X, a)` over the permitted safe action set for each
event, and the dominance property `EV_true(O1) ≤ EV_true(oracle)` is asserted **per event**,
not inferred from aggregate means. SNIPS is not used anywhere in this check.

---

## 7. SNIPS evaluation (estimator)

```
Logged epsilon-greedy realized EV: INR 1,596.19 / event
Baseline SNIPS EV:                 INR 1,676.60   95% CI [1,567.68, 1,785.87]  SE 54.64
                                   coverage 72.71%   matched 10,906   ESS 5,333.6
O1 SNIPS EV:                       INR 2,415.74   95% CI [2,088.89, 2,861.67]  SE 201.53
                                   coverage 37.80%   matched  5,670   ESS 1,724.6  (11.5% of N)
Min logging propensity:            0.075        Max importance weight: 13.33
Weight clipping applied:           False
SNIPS uplift over baseline:        INR 739.14 / event
SNIPS minus direct true EV:        + INR 62.20  (0.31 SE - estimator variance, not gain)
```

---

## 8. Oracle evaluation

The oracle is the per-event maximum of true EV over the **safe** action set, so it is an
upper bound the policy cannot exceed by construction — and that is now verified rather than
assumed. Oracle values are computed only **after** the policy has selected its action, from
`compute_true_recovery_probability`, which no component of the decision path imports.

| | Value |
| :--- | ---: |
| Mean oracle best EV | ₹2,356.66 |
| Mean O1 EV | ₹2,353.54 |
| Mean regret | ₹3.12 |
| Episodes where regret < 0 | **0** |
| Minimum per-event regret | 0.000000 |

---

## 9. Safety Gate verification

| Property | Result |
| :--- | :--- |
| Supported categories enumerated | 13, derived from `FAILURE_TAXONOMY` |
| Every supported category yields a non-empty subset of the action space | Verified (13 subtests) |
| `do_nothing` always available | Verified |
| Non-retryable categories collapse to `do_nothing` | Verified (3 subtests) |
| Technical failures never offer `update_information` | Verified (8 subtests) |
| Stale-info categories exclude blind retries | Verified (2 subtests) |
| Retry cap ≥ 3 collapses to `do_nothing` for every category | Verified (13 subtests) |
| **`update_information` offered only where the specification allows** | Verified — the core invariant, stated positively |
| Unknown / malformed categories fail closed | Verified (11 subtests × 2 assertions) |
| Non-string categories fail closed | Verified (5 subtests) |
| Agent stays fail-closed with API validation bypassed | Verified (3 subtests) |
| API rejects unknown enum values with HTTP 422 | Verified |
| Safety violations on the test set | **0 / 15,000 (0.00%)** |

---

## 10. A3 ablation correction

Covered in §3.6. Summary of the required reporting fields:

```
N (population):                 15,000
Valid evaluated events:         15,000
Missing events:                      0
A3 mean true EV:            INR 2,454.54
A0 baseline mean true EV:   INR 1,671.74
A4 (full architecture) EV:  INR 2,353.54
A3 safety violations:           12,485  (83.23%)
```

---

## 11. Distribution-shift correction

Covered in §3.7. All four shifts now recompute ground truth on the shifted contexts, update
taxonomy-derived fields consistently, and emit
`ground_truth_recomputed_on_shifted_context: true`, `events_evaluated`,
`per_event_dominance_violations` and `ranking_stable`.

---

## 12. Validation / test metric distinction

Covered in §3.9. The distinction is now enforced structurally: selection reads
`validation_metrics`, the report carries all three splits with an explicit bias note, and the
README, TASK_11, TASK_14, dashboard and both pitch documents quote the **test** figures as
model quality with the validation figures shown alongside and labelled as the selection split.

---

## 13. Leakage verification

Re-verified after all changes. **No relaxation was introduced.**

| Check | Result |
| :--- | :--- |
| `ALL_PREDICTOR_FEATURES` | 24 context + 1 action = 25; no outcome or oracle field |
| Column selection | `prepare_feature_dataframe` selects explicitly by name |
| `ColumnTransformer` | `remainder="drop"` — extra columns cannot reach the estimator |
| `SYNTHETIC_ORACLE_ONLY_*` in decision path | **None** — evaluation modules only |
| `compute_true_recovery_probability` imported by advisor / agent / API / predictor | **No** |
| Oracle read before action selection | **No** — read only after, and only to score |
| `/decide` response or audit `input_context` contains oracle/outcome keys | **No** (asserted in `test_task14_e2e.py` and re-verified live) |
| New `compute_true_ev_matrix` | Evaluation-side only; not imported by any decision component |

The new ground-truth-robustness experiment uses the simulator, but only to **score** an
already-frozen policy — the policy's action selection is computed once, outside the scenario
loop, precisely so that it cannot vary with the ground truth being applied.

---

## 14. Test results

```
python -m pytest tests/ -q
83 passed, 123 subtests passed in 27.17s
```

| Suite | Tests | Notes |
| :--- | ---: | :--- |
| `test_generator.py` | 6 | unchanged |
| `test_anti_circularity.py` | 8 | unchanged |
| `test_task11_policy.py` | 13 | +4 new (overlap diagnostics, full-population coverage, per-event dominance, misaligned-join rejection) |
| `test_task12_robustness.py` | 10 | unchanged; `test_10` now passes against a genuinely `true` `ranking_stable` |
| `test_task13_agent.py` | 4 | unchanged |
| `test_task13_api.py` | 5 | unchanged |
| `test_task13_executor.py` | 5 | unchanged — the new executor checks did not break existing behaviour |
| `test_task14_e2e.py` | 6 | unchanged |
| **`test_task16b_safety_regression.py`** | **27 (+123 subtests)** | **new** |

No test was removed, disabled or weakened. `test_task11_policy.py::test_10` was updated for
the renamed report key and **strengthened** at the same time.

---

## 15. Reproducibility verification

All commands executed; results are not inferred from source inspection.

| Stage | Command | Result |
| :--- | :--- | :--- |
| Dataset regeneration | `python src/data/generate_synthetic.py --config configs/synthetic_config.yaml --events 100000 --outdir data/synthetic` | 70k/15k/15k, alignment assertions pass |
| Determinism | regenerate to a scratch dir, compare SHA-256 | **6/6 byte-identical** |
| Manifest | `python scripts/generate_data_manifest.py` | checksums regenerated, verify PASS |
| Model training | `python scripts/train_recovery_model.py` | 6 candidates; `hist_gb_calibrated` selected |
| Policy evaluation | `python scripts/evaluate_policy.py` | 4 figures + JSON |
| Robustness | `python scripts/run_robustness.py` | 5 phases, 5 figures + JSON |
| Evaluation determinism | re-run both scripts, compare JSON | **identical** |
| Test suite | `python -m pytest tests/ -q` | **83 passed, 123 subtests** |
| Frontend typecheck + build | `npm run build` (`tsc && vite build`) | **0 TypeScript errors**, built in 2.31s |
| Demo | `python scripts/demo_agent.py` | decision → execution → audit, 0 safety violations |
| API | `/health`, `/events`, `/reports/summary`, `/decide`, `/execute`, `/audit/{id}` | all verified incl. rejection paths |
| Model loads under documented env | `RecoveryPredictor.load(...)` | loads, **no version warnings**, sklearn 1.9.0 |

Environment: Python 3.11.9, Windows AMD64; numpy 2.3.2, pandas 2.3.2, scikit-learn 1.9.0,
scipy 1.17.1, PyYAML 6.0.3, matplotlib 3.11.1, joblib 1.5.3, fastapi 0.139.2, pydantic 2.13.4,
pytest 9.1.1 — pinned in `requirements-lock.txt`.

---

## 16. Remaining limitations

Honest disclosure of what this task did **not** fix.

1. **Regret is a fragile statistic here.** ₹3.12 against a ₹2,356.66 ceiling is 0.13%. Across
   three data draws it has read ₹0.94, ₹1.63 and ₹3.12. Treat it as "small and positive",
   not as a precise figure. No confidence interval is reported for regret itself.
2. **The evaluated policy is still not the deployed policy** (audit M-6). Reported EVs come
   from pure `argmax` over the safe set; the served `RecoveryAgent` additionally applies
   stopping rules and low-confidence escalation, which would block execution on **4.45%** of
   test episodes. This is now documented but not unified — doing so would change what the
   headline measures, which belongs in a separate task.
3. **The baseline remains close to the data-generating policy** (audit M-7): ~88% action
   agreement with the logging heuristic. Now stated in the README limitations.
4. **Near-oracle efficiency remains partly structural.** Every hidden interaction is a
   deterministic function of observed features, so there is no unobserved confounding. Now
   stated in the README limitations.
5. **The "temporal" split still carries no temporal structure** — timestamps are i.i.d. and
   sorted. Now stated in `DATASET_CARD.md` and the README rather than being fixed, because
   introducing genuine drift would change the dataset's character.
6. **No authentication or authorization on any endpoint.** Out of scope: the executor is
   simulation-only and adding auth would be production functionality. `/audit/{id}` still
   returns full context to any caller.
7. **`AuditStore` remains in-memory and unbounded** — no persistence, no eviction.
8. **Cross-field consistency is not validated.** A caller may still send
   `amount: 50000` with `order_value_tier: "low"`, or a `failure_code` that does not belong to
   the supplied `failure_category`. Each field is individually in-vocabulary; the combination
   is not checked. Existing test fixtures rely on this.
9. **10.36% of events carry `currency: "USD"`** while `amount` is used directly as V against
   rupee costs. Internally consistent only because currency is decorative.
10. **`predict_proba` still rounds to 4 decimals**, worth up to ~₹10 of EV error at the
    largest test amount.
11. **The `NON_POSITIVE_EV` stopping rule fires on 0 test episodes**, so it remains
    exercised only by construction, not by data.
12. **`compute_true_ev_matrix` is O(N × |A|) in Python**, adding ~50s to the robustness suite.
    Correctness was preferred over speed.

---

## 17. Files changed

See §4 for the change description per file. Full list, 30 files:

**Source (9):** `src/data/generate_synthetic.py`, `src/data/failure_taxonomy.py`,
`src/data/safety.py`, `src/data/ground_truth.py`, `src/api/schemas.py`, `src/api/app.py`,
`src/agent/executor.py`, `src/policy/evaluation.py`, `src/evaluation/robustness.py`

**Scripts (3):** `scripts/train_recovery_model.py`, `scripts/evaluate_policy.py`,
`scripts/run_robustness.py`

**Tests (2):** `tests/test_task16b_safety_regression.py` (new), `tests/test_task11_policy.py`

**Frontend (3):** `frontend/src/components/Evaluation.tsx`,
`frontend/src/components/Overview.tsx`, `frontend/src/types/api.ts`

**Dependencies (2):** `requirements.txt`, `requirements-lock.txt` (new)

**Regenerated artifacts (9):** `data/synthetic/{train,val,test}.csv`,
`data/synthetic/{train,val,test}_oracle.csv`, `data/synthetic/checksums.json`,
`models/recovery_predictor.joblib`, `reports/task11_model_results.json`,
`reports/task11_policy_evaluation.json`, `reports/task12_robustness.json`,
`reports/figures/**` *(dataset, model and figures are gitignored)*

**Documentation (10):** `README.md`, `TASK_11_RESULTS.md`, `TASK_12_ROBUSTNESS.md`,
`TASK_13B_DASHBOARD.md`, `TASK_14_E2E_VALIDATION.md`, `TASK_15_SUBMISSION_PACKAGE.md`,
`TASK_16_REPRODUCTION_AUDIT.md` (banner only), `DATASET_CARD.md`, `docs/DEMO.md`,
`docs/PITCH_5_MINUTES.md`, `docs/PITCH_SLIDES.md`, `scripts/demo_full_stack.md`,
`docs/audits/TASK_16A_INDEPENDENT_SCIENTIFIC_AUDIT.md` (banner only),
`TASK_16B_SCIENTIFIC_CORRECTIONS.md` (this file)

---

## 18. Correction summary table

| Finding | Audit claim | Root cause | Correction | Verification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C-1** | Oracle misaligned; 114 test events unmatched; merge yields 15,015 rows; regret invalid | `randint` ids collide (57×) → label-based `.loc` reindex expands oracle frame → both frames sliced with `len(df_obs)` boundaries | Sequential unique ids; positional permutation for both frames; alignment assertions at 3 points; `validate="one_to_one"` joins | 100k unique ids, 0 duplicates, positional alignment true in all splits, merge = 15,000, 0 NaN; regression test rejects a corrupted frame | **FIXED** |
| **C-2** | Safety Gate fails open on unknown category | Deny-list with no terminal branch; no enum validation on input | Rule 0 default-deny + `isinstance` guard; closed enums at API (HTTP 422); no normalization | 11 malformed inputs → 422 at API, `do_nothing` at domain layer; 3 bypass probes fail closed | **FIXED** |
| **C-3a** | Fabricated action distribution | Metrics restated as literals, drifted from artifacts | Dashboard renders from `/reports/summary`; docs regenerated | Live values match `reports/task11_policy_evaluation.json` | **FIXED** |
| **C-3b** | Robustness matrix matches no run | Same | Same | Repo-wide grep: 0 stale metrics outside historical audits | **FIXED** |
| **C-3c** | Ground-truth robustness never implemented | Config key existed; no consumer; import unused | `interaction_scale` in simulator + `run_ground_truth_robustness()` + phase 5 | 3 scenarios in JSON; default proven no-op by identical checksums | **IMPLEMENTED** |
| **C-3d** | "STABLE" contradicts `ranking_stable: false` | `np.mean` over NaN-containing arrays | C-1 removes NaNs; explicit casts; field emitted for all families | `ranking_stable: true` in all 13 scenarios; docs read the field | **FIXED** |
| **M-1** | A3 EV computed on 15.8% of events | Oracle CSV stores NaN for unsafe actions; `nanmean` drops them | `compute_true_ev_matrix()` for all actions/rows; explicit denominators; no-NaN assertion | A3: 15,000/15,000 scored, ₹2,454.54; finding reframed | **FIXED** |
| **M-2** | Shifts scored against unshifted ground truth | Features mutated; oracle read from original CSV | Ground truth recomputed on shifted contexts; derived fields updated | 4 shifts emit `ground_truth_recomputed_on_shifted_context: true`; values moved up to ₹309 | **FIXED** |
| **M-3** | SNIPS headlined without uncertainty | No variance estimate anywhere | `bootstrap_snips_ci()`; report split into authoritative vs estimator; overlap diagnostics | O1 SNIPS ₹2,415.74 [2,088.89, 2,861.67]; gap to direct = 0.31 SE | **FIXED** |
| **M-4** | Validation metrics labelled as test | Selection and reporting both on `val.csv`; no test scoring | Test scored once after selection; 3 splits reported with bias note | Test AUC 0.8600 / Brier 0.1485 now headline | **FIXED** |
| **M-5** | Executor allows replay and id spoofing | `payment_id` never compared; `execution_status` never read back | Payment binding + replay rejection checks | Replay → 400; spoofed id → 400; 6 regression tests | **FIXED** |
| **M-6** | Evaluated policy ≠ deployed policy | Evaluation omits stopping rules/escalation | Documented; 4.45% escalation rate disclosed | README limitation §16.2 | **DOCUMENTED** |
| **M-7** | Baseline ≈ logging heuristic | By construction of the environment | Documented | README limitation §16.3 | **DOCUMENTED** |
| **N-1** | Schema defaults outside vocabulary | Defaults never checked against training data | In-vocabulary defaults; closed enums | Encoder-recognition test: every categorical block non-zero | **FIXED** |
| **N-1b** | `is_subscription` int vs bool | — | None needed | Identical predictions (0.273 both); evidence in §3.11 | **NOT REPRODUCIBLE** |
| **NEW** | Defaulted enum fields leak `Enum` members | Pydantic v2 skips default validation | `validate_default=True` | All 12 categorical fields serialize as plain `str` | **FIXED** |

---

## 19. Git commit

```
Commit:  __COMMIT_HASH__
Branch:  audit/task16b-scientific-corrections
Message: fix: correct scientific evaluation and safety audit findings
```

Nothing was pushed. No remote was configured. `main` was not modified. History was not
rewritten.

---

> [!IMPORTANT]
> **TIER C DISCLOSURE.** Every figure in this document was produced inside the project's
> synthetic evaluation environment. All recovery probabilities, action outcomes and economic
> values are generated by a hidden simulator. In our synthetic evaluation environment O1
> attains the results above; these are **not** measured Razorpay production performance, real
> customer recovery probabilities, or real money movement, and must not be presented as such.
