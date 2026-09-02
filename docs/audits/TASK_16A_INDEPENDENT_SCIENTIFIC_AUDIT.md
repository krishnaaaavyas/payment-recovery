# Task 16A — Independent Scientific Audit

> [!NOTE]
> **AUDIT OF THE PRE-CORRECTION REPOSITORY — retained as evidence.**
>
> This audit was performed read-only against commit `156a4cc`. Its findings were acted on in
> Task 16B; the defects it identifies (oracle misalignment, safety-gate fail-open,
> untraceable published figures, A3 denominator, distribution-shift ground truth,
> validation-vs-test labelling, executor replay) have since been fixed. The "published"
> figures it quotes are therefore historical, and its recomputed figures were derived from
> the pre-correction dataset.
>
> **Nothing in this file has been edited to match the corrected results.** For the
> corrections and current authoritative metrics see `TASK_16B_SCIENTIFIC_CORRECTIONS.md`.

---

> **Project**: O1 — Payment Failure Economic Recovery Advisor
> **Track**: Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery
> **Audit type**: Independent, adversarial, read-only falsification audit
> **Audit date**: 2026-09-02

---

## 0. How to read this document

This audit was conducted under the explicit instruction to **find problems, not to confirm the
project**, and to treat every prior report (`TASK_11` – `TASK_16`), README claim, code comment and
generated summary as an unverified claim rather than as evidence.

Four categories of statement are kept strictly separate throughout, and are labelled inline:

| Label | Meaning |
| :--- | :--- |
| **EVIDENCE** | Something directly observable in the repository — a line of code, a committed file, a config value, a JSON field. Verifiable by reading the repo. |
| **RECOMPUTED** | A number this audit derived independently by executing code against the committed dataset/model. The derivation method is stated in each case. |
| **INTERPRETATION** | The auditor's reading of what the evidence means. Debatable. |
| **RECOMMENDATION** | A proposed change. Nothing in this audit was applied. |

**No source code, test, dataset, configuration, report or document was modified during this audit.**
This file is the only artifact it created.

---

## 1. Audit scope

### 1.1 In scope

| Area | Coverage |
| :--- | :--- |
| Repository structure | Complete inventory; source-of-truth vs generated artifacts; dead/duplicated code |
| Data generation | `src/data/` — taxonomy, safety gate, economics, logging policy, ground truth, generator, validation |
| Data leakage / circularity | `ALL_PREDICTOR_FEATURES`, preprocessing, training, feature engineering, API input transformation, policy evaluation |
| Model | Class, preprocessing, categorical/numerical handling, calibration, split usage, hyperparameter selection, random state, serialization, inference path |
| Economic value model | Authoritative `EV(a\|X)` implementation, units, sign conventions, action dependence, consistency across call sites |
| Safety gate | Every rule; what each removes; whether unsafe actions can reach execution; backend authority; pre-decision-only dependence |
| Policy | `PolicyAdvisor`, `RecoveryAgent`, candidate set, filtering, EV maximization, `do_nothing`, stopping rules, escalation, confidence, retry cap, determinism |
| Off-policy evaluation | IPS/SNIPS derivation, propensities, weights, normalization, support, overlap, clipping, ESS, coverage |
| Direct ground-truth evaluation | Oracle isolation, ordering of action selection vs truth lookup, per-event regret, full-population coverage |
| Task 12 robustness | Economic sensitivity, ablation, distribution shifts, stress cases, ground-truth interaction scaling |
| API / agent | FastAPI routes, Pydantic models, agent, executor, audit store, authorization, determinism, failure handling |
| Frontend | Logic duplication, oracle exposure, metric fidelity, endpoint correspondence, synthetic disclosure |
| Tests | What each suite proves and does not prove; assertion strength; anti-circularity tests specifically |
| Reproducibility | Dataset, model, evaluation, reports, API, frontend; dependency pinning |
| Claims | README, `docs/`, `TASK_*.md`, `frontend/`, `reports/` |

### 1.2 Explicitly out of scope

- Business viability, market sizing, or competitive positioning of the O1 concept.
- The `.xlsx` / `.docx` research artifacts from Tasks 2–9 (read for context only; not audited).
- Front-end visual design, accessibility, or build tooling beyond metric fidelity.
- Any judgement about real Razorpay production systems. **This audit makes no claim about
  production payment recovery.** All numbers below describe a synthetic environment.

---

## 2. Repository commit audited

**EVIDENCE**

```
HEAD commit:   156a4cc  audit: verify clean environment reproduction
Parent:        f9c5f0b  docs: finalize buildathon submission package
Grandparent:   35469bb  test: harden end-to-end evaluation and demo
Working tree:  clean (no uncommitted modifications at audit start)
```

The commit immediately preceding the audit (`156a4cc`) added only
`TASK_16_REPRODUCTION_AUDIT.md` (197 insertions, 1 file changed).

**INTERPRETATION**: the prior audit committed a narrative report but no re-derived data, so its
claims could not be checked against any artifact it produced. They were therefore re-derived from
scratch here.

---

## 3. Branch audited

**EVIDENCE**

```
Branch audited:  audit/task16a-independent-scientific
Default branch:  main
Git author:      Krishna Vyas
```

---

## 4. Environment information

**EVIDENCE** — the environment in which all recomputations below were executed.

| Component | Version |
| :--- | :--- |
| OS | Windows 11 Home Single Language 10.0.26200 (x86_64) |
| Python | 3.11.9 (CPython, MSC v.1938 64-bit) |
| scikit-learn | 1.9.0 |
| numpy | 2.3.2 |
| pandas | 2.3.2 |
| scipy | 1.17.1 |
| joblib | 1.5.3 |
| pytest | present; 53 tests collected, 53 passed |

**EVIDENCE** — `requirements.txt` specifies only lower bounds (`>=`) for all 11 dependencies. There
is no lockfile, no `constraints.txt`, and no record of the scikit-learn version that produced the
committed `models/recovery_predictor.joblib`.

**INTERPRETATION**: reproduction succeeded on this environment (§9.3, §9.4), but the repository does
not pin the environment that would make that guarantee portable. A pickled scikit-learn pipeline is
version-sensitive.

---

## 5. Evidence-gathering methodology

Every quantitative statement in this audit was derived by one of the following methods. The method
is named at each finding.

**M1 — Direct source reading.** All Python source (`src/`, `scripts/`, `tests/`), all configs, and
the frontend TypeScript were read in full — approximately 5,500 lines. No conclusion below rests on
a docstring, comment, README statement, or prior task report.

**M2 — Independent recomputation from the generator, bypassing the evaluation pipeline.** For the
ground-truth ("oracle") checks, this audit did **not** read the committed `*_oracle.csv` files.
Instead it loaded `data/synthetic/test.csv`, recomputed the safe action set with
`evaluate_safety_gate`, recomputed true probabilities with `compute_true_recovery_probability`, and
recomputed true EV with `calculate_ev` — for every one of the 15,000 test events and every safe
action. This is the only way to obtain ground truth immune to the defect described in §7.1.

**M3 — Pipeline reproduction.** `generate_dataset()` was re-run into a scratch directory outside the
repository and SHA-256-compared against `data/synthetic/checksums.json`. The selected model was
retrained from `train.csv` and re-scored on all three splits. `run_policy_evaluation()` was re-run
and compared field-by-field against the committed `reports/task11_policy_evaluation.json`.

**M4 — Adversarial API probing.** The FastAPI application was driven through
`fastapi.testclient.TestClient` with deliberately malformed and hostile payloads: case-variant
categories, whitespace-padded categories, novel categories, decision replay, payment-id
substitution, and unauthenticated audit reads.

**M5 — Statistical resampling.** SNIPS and IPS estimators were re-implemented from their
definitions and bootstrapped with 2,000 replicates (seed 0) to obtain the confidence intervals the
repository does not report.

**M6 — Cross-artifact tracing.** Every quantitative figure appearing in `README.md`, `TASK_*.md`,
`docs/` and `frontend/src/` was grepped against `reports/*.json` to establish whether a committed
run produced it.

---

## 6. Overall verdict

# NEEDS CORRECTION

**INTERPRETATION**

Not **FAIL**. The scientific foundation is real and survives adversarial inspection: there is no
oracle or outcome leakage into the model, the ground-truth simulator is genuinely separated from the
learned estimator, the pipeline is bit-exactly reproducible, the off-policy mathematics is correct
with genuine action support, and the TIER C synthetic disclosure is consistent and honest across
every document.

Not **PASS WITH CAVEATS**. Three defects are of a kind an evaluator would treat as disqualifying if
found independently: a dataset alignment defect that corrupts the flagship regret and efficiency
figures; a safety gate that approves customer-facing interventions on any input string it does not
recognize; and at least four sets of published numbers — including an entire report section
describing an experiment that has no implementation — that cannot be traced to any code or output in
the repository.

**The most important finding is that correcting the errors does not overturn the project's
conclusions.** Recomputed honestly over the full population, O1 still attains 99.93% of the oracle
ceiling and still beats the deterministic baseline by ₹683.29 per event. The work is stronger than
its write-up; the write-up is what must change.

---

## 7. Critical issues

### 7.1 CRITICAL C-1 — Oracle / test-event misalignment corrupts every Task 11 ground-truth figure

#### Evidence

`src/data/generate_synthetic.py:94`

```python
event_ids = [f"evt_{x}" for x in rng.randint(10000000, 99999999, size=N)]
```

Drawing 100,000 identifiers **with replacement** from a space of 9×10⁷ produces birthday collisions
with near-certainty.

`src/data/generate_synthetic.py:228-229`

```python
df_obs = df_obs.sort_values("failure_timestamp").reset_index(drop=True)
df_oracle = df_oracle.set_index("event_id").loc[df_obs["event_id"]].reset_index()
```

With a duplicated index label, `.loc[list_of_labels]` returns **every** matching row for **each**
requested occurrence — so a label appearing twice in both frames yields four rows. `df_oracle`
therefore grows longer than `df_obs`.

`src/data/generate_synthetic.py:238-246`

```python
N = len(df_obs)
train_end = int(N * cfg["splits"]["train"])
val_end   = int(N * (cfg["splits"]["train"] + cfg["splits"]["val"]))
...
obs_sub = df_obs.iloc[s:e]
ora_sub = df_oracle.iloc[s:e]      # same boundaries applied to a longer frame
```

Both frames are sliced with boundaries computed from `len(df_obs)`. The oracle frame is
progressively shifted relative to the observed frame, and its tail is truncated.

`src/policy/evaluation.py:180`

```python
df_merged_ora = df_eval.merge(df_test_oracle, on="event_id", how="left")
```

No `drop_duplicates`, no `validate=` argument.

`src/policy/evaluation.py:195-198`

```python
mean_oracle_best_ev = float(df_test_oracle["SYNTHETIC_ORACLE_ONLY_true_best_ev"].mean())
mean_oracle_ml_ev   = float(np.nanmean(oracle_true_ev_ml))
regret = float(mean_oracle_best_ev - mean_oracle_ml_ev)
```

`mean_oracle_best_ev` is a plain mean over the 15,000 rows of `test_oracle.csv`;
`mean_oracle_ml_ev` is a `nanmean` over the merged frame. **These are different row sets.**

For contrast, the Task 12 code path already contains the fix, at four separate call sites —
`src/evaluation/robustness.py:91, 213, 337, 432`:

```python
df_ora_clean = df_test_oracle.drop_duplicates("event_id")
```

#### Recomputed (M2, M3)

Duplicate identifiers actually present in the committed dataset:

| Split | Observed rows | Duplicate `event_id` in obs | Duplicate `event_id` in oracle |
| :--- | ---: | ---: | ---: |
| train | 70,000 | 32 | 114 |
| val | 15,000 | 4 | 25 |
| test | 15,000 | 1 | 12 |
| **total** | **100,000** | **57** | — |

Positional correspondence between `<split>.csv` row *i* and `<split>_oracle.csv` row *i*:

| Split | Positionally aligned? | First mismatching row index |
| :--- | :--- | ---: |
| train | No | 829 |
| val | No | 0 (entirely misaligned) |
| test | No | 0 (entirely misaligned) |

Set-level correspondence for the test split:

| Measurement | Value |
| :--- | ---: |
| Test events with **no** row in `test_oracle.csv` | **114** |
| Rows in `test_oracle.csv` belonging to **validation** events | **103** |
| Rows produced by the un-deduplicated merge at `evaluation.py:180` | **15,015** (vs 15,000) |
| Rows in the merged frame with `NaN` oracle EV, silently dropped by `nanmean` | **114** |

A concrete example of cross-contamination: `evt_71766967` appears twice in `test.csv` — once as a
`blocked_instrument` failure of ₹3,915.56 and once as an `issuer_unavailable` failure of ₹2,640.94 —
and twice in `test_oracle.csv` with different `baseline_action` values. The merge cross-joins them,
attaching each oracle row to both observed events.

Ground truth recomputed directly from the generator over the complete, correctly matched
15,000-event population (M2):

| Quantity | Published (`reports/task11_policy_evaluation.json`) | **Recomputed (this audit)** | Delta |
| :--- | ---: | ---: | ---: |
| Direct true O1 policy EV | ₹2,349.72 | **₹2,355.03** | +₹5.31 |
| Direct true oracle best EV | ₹2,350.67 | **₹2,356.66** | +₹5.99 |
| Direct true baseline EV | ₹1,668.04 | **₹1,671.74** | +₹3.70 |
| **Direct true regret** | **₹0.94 / event** | **₹1.63 / event** | **+₹0.69 (+73%)** |
| **Policy efficiency** | **99.96%** | **99.93%** | −0.03 pp |
| Direct uplift over baseline | (not published) | **₹683.29 / event (+40.87%)** | — |
| Events with negative regret | (not checked) | **0 of 15,000** | — |

**EVIDENCE — the repository already contradicts itself.** `reports/task12_robustness.json`
→ `economic_sensitivity.BASELINE` — which uses the `drop_duplicates` path — reports
`regret_ci.mean = 1.56` and `ml_policy_ev_ci.mean = 2349.89` for the *identical* experiment.
`TASK_12_ROBUSTNESS.md §8.6` acknowledges both values ("₹0.94–₹1.56 per event") without explaining
why one experiment yields two answers. `README.md` and the dashboard quote only ₹0.94.

#### Interpretation

The published "regret" is a difference between two means computed over two **non-matching
populations**. Regardless of its magnitude, it is not a regret in the decision-theoretic sense. The
error is small in absolute terms (₹0.69/event on a ₹2,350 base), but it is of the *same order of
magnitude as the quantity being reported* — ₹0.94, against a contamination affecting 0.76% of rows —
so the headline figure is not robust to the defect.

Separately, this defect is the root cause of two downstream symptoms documented elsewhere in this
report: the `ranking_stable: false` flag in §7.3(d), and the test that masks it in §11.

#### Recommendation

See **R-1** and **R-2** in §13.

---

### 7.2 CRITICAL C-2 — The Safety Gate fails open on any unrecognized `failure_category`

#### Evidence

`src/data/safety.py:9-47`. The function's own docstring states:

```python
"""
Returns (safe_actions, constraints_applied).
Guarantees ML model or policy can NEVER choose an illegal action.
"""
```

The implementation is a **deny-list**, not an allow-list:

```python
cat = context.get("failure_category", "")
...
if cat in ["hard_decline", "blocked_instrument", "velocity_limit"]:
    return ["do_nothing"], constraints_applied     # Rule 1
if retry_count >= 3:
    return ["do_nothing"], constraints_applied     # Rule 2
safe = set(ALL_ACTIONS)                            # <-- default: everything allowed
if cat in ["expired_card", "invalid_information"]: ...   # Rule 3
if cat in [...eight technical categories...]:      ...   # Rule 4
return sorted(list(safe)), constraints_applied
```

There is no terminal `else` branch and no membership check against `FAILURE_TAXONOMY`. Any string
that matches none of the hard-coded lists falls through to the full five-action set with an **empty
constraint list**.

`src/api/schemas.py:23-30` — the API applies no enum, `Literal`, or pattern constraint:

```python
failure_code: str     = Field(..., description="Taxonomy failure code", ...)
failure_category: str = Field(..., description="Taxonomy failure category", ...)
```

`RecoveryAgent.decide` (`src/agent/recovery_agent.py:124`) checks only `rec_act not in safe_actions`
— which is vacuously satisfied when `safe_actions` is everything.

#### Recomputed (M4)

Live probes against `POST /decide`, all with an otherwise-identical ₹50,000 stolen-card payload:

| `failure_category` sent | Action returned | `status` | `safe` | `execution_available` | `safety_rule` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `"hard_decline"` | `do_nothing` | `APPROVED` | `true` | `true` | `HARD_SAFETY_NON_RETRYABLE_HARD_DECLINE` |
| `"HARD_DECLINE"` | `update_information` | `APPROVED` | `true` | `true` | `""` (empty) |
| `" hard_decline "` | `update_information` | `APPROVED` | `true` | `true` | `""` (empty) |
| `"chargeback_fraud_confirmed"` | `update_information` | `APPROVED` | `true` | `true` | `""` (empty) |

The `OneHotEncoder(handle_unknown="ignore")` at `src/models/preprocessing.py:61` compounds this: the
unrecognized category is encoded as an all-zero block, so the model still returns a confident
probability rather than signalling that the input is out of distribution.

#### Interpretation

A fraud or blocked-instrument decline arriving with different letter casing, stray whitespace, or a
taxonomy code introduced after this code was written is **approved for a customer-facing
intervention, with no constraint recorded in the audit trail**. The failure mode is silent: the
response is indistinguishable from a legitimate approval.

This does not invalidate the 0.00% safety-violation measurement — that measurement is correct for the
synthetic test set, where categories are canonical by construction. It does mean the claim "0.00%
safety violations across **all operations**" (`README.md:112`) is unsupported for any input outside
that distribution, and that the docstring's "can NEVER" is false.

**INTERPRETATION**: this is the single most serious finding from a deployment standpoint, because the
safety gate is the architectural claim the project is built around.

#### Recommendation

See **R-3** in §13.

---

### 7.3 CRITICAL C-3 — Published figures that exist in no code, no report, and no run

Four distinct sets of numbers are presented as measured results but cannot be traced to any artifact
in the repository (M6).

#### (a) The O1 action distribution is fabricated

**EVIDENCE** — `TASK_11_RESULTS.md:78-86` and `frontend/src/components/Overview.tsx:9-15` both
publish the same figures, described as "Action selection share across 15,000 test payment failure
episodes":

| Action | Published as O1 share | **Actual** (`reports/task11_policy_evaluation.json` → `distributions.ml_action_distribution`) |
| :--- | ---: | ---: |
| `retry_later` | 41.2% | **0.89%** |
| `retry_now` | 21.8% | **0.03%** |
| `switch_method` | 18.5% | **69.45%** |
| `do_nothing` | 10.7% | **15.41%** |
| `update_information` | 7.8% | **14.21%** |

**RECOMPUTED (M2)** — independent recomputation confirms the JSON, not the documents:
`switch_method` 69.45%, `do_nothing` 15.41%, `update_information` 14.21%, `retry_later` 0.89%,
`retry_now` 0.03%.

These are not rounding differences, and they match **no policy in the repository**. For comparison,
the deterministic baseline (`task12_robustness.json` → `A0_Rule_Baseline`) is `retry_now` 38.89% /
`retry_later` 27.39% / `do_nothing` 15.41% / `update_information` 14.33% / `switch_method` 3.98%; and
the logged ε-greedy policy in `test.csv` is `do_nothing` 26.82% / `retry_later` 24.83% / `retry_now`
23.81% / `switch_method` 13.05% / `update_information` 11.48%.

The baseline column of the same `TASK_11_RESULTS.md` table is also wrong — by up to 8.8 percentage
points on `retry_later`.

#### (b) The robustness matrix in the README and the dashboard matches nothing

**EVIDENCE** — `README.md:140-146` and `frontend/src/components/Evaluation.tsx:145-177` publish:

| Scenario (as labelled) | Baseline EV | O1 EV | Oracle EV | In `task12_robustness.json`? |
| :--- | ---: | ---: | ---: | :--- |
| Baseline Scenario | ₹1,668.04 | ₹2,349.72 | ₹2,350.67 | No — JSON says 1,669.04 / 2,349.89 / 2,350.91 (the published row is the *Task 11* figures) |
| High Retry Cost (2.5x) | ₹1,659.54 | ₹2,343.83 | ₹2,344.82 | **No — zero occurrences.** JSON: 1,666.24 / 2,345.39 / 2,346.45 |
| High Friction (2.0x) | ₹1,656.32 | ₹2,345.92 | ₹2,347.01 | **No — zero occurrences.** JSON: 1,664.84 / 2,340.06 / 2,341.35 |
| Distribution Shift (3.0x Amount) | ₹5,004.12 | ₹7,057.89 | ₹7,060.75 | **No — zero occurrences.** JSON: 5,023.19 / 7,078.57 / 7,081.14 |

A grep for `5004.12|7057.89|1659.54|2343.83` across `reports/task12_robustness.json` returns **zero
matches**.

Additionally, the scenario is labelled **"High Retry Cost (2.5x)"** while
`configs/robustness_config.yaml:23-27` defines `cost_multiplier: 2.0`.

#### (c) The "Ground-Truth Robustness" experiment has no implementation

**EVIDENCE** — `TASK_12_ROBUSTNESS.md:54-58` reports:

> - **WEAKER_CONTEXTUAL_INTERACTIONS (0.5x)**: Regret remains bounded at ₹1.12 / event.
> - **STRONGER_CONTEXTUAL_INTERACTIONS (1.5x)**: Regret remains bounded at ₹2.05 / event.

- `configs/robustness_config.yaml:39-45` defines a `ground_truth_robustness` block with
  `interaction_scale` values 1.0 / 0.5 / 1.5.
- **No code reads that key.** A grep for `ground_truth_robustness` and `interaction_scale` across
  `src/` and `scripts/` returns no consumer.
- `scripts/run_robustness.py:154-173` runs exactly four phases — economic sensitivity, ablation,
  distribution shifts, stress testing. There is no ground-truth-scaling phase.
- `reports/task12_robustness.json` has exactly four top-level keys and no `ground_truth_robustness`.
- `src/evaluation/robustness.py:21` imports `compute_true_recovery_probability` — and **never calls
  it**.

The two regret figures have no source. `TASK_12_ROBUSTNESS.md §2` additionally depicts this phase in
its ASCII experiment diagram as though it had run.

#### (d) "STABLE" is asserted where the project's own report says otherwise

**EVIDENCE** — `reports/task12_robustness.json` contains `"ranking_stable": false` for **all six**
economic sensitivity scenarios. Meanwhile:

- `README.md:142-145` displays "**STABLE**" for every row.
- `frontend/src/components/Evaluation.tsx:158, 166, 174, 182` displays "STABLE" for every row.
- `TASK_12_ROBUSTNESS.md:52` states the ranking "remains 100% stable across all economic
  perturbations."

**RECOMPUTED** — root cause identified. `src/evaluation/robustness.py:170`:

```python
"ranking_stable": bool(np.mean(ora_best_arr) >= np.mean(ora_ml_arr) - 1e-5
                       and np.mean(ora_ml_arr) >= np.mean(ora_base_arr) - 1e-5),
```

`np.mean` (not `np.nanmean`) is applied to arrays containing the 114 `NaN` entries introduced by C-1.
`np.mean` of an array containing `NaN` returns `NaN`, and every comparison against `NaN` is `False`.
The adjacent confidence-interval fields use `np.nanmean` and are therefore populated normally, which
is why the inconsistency is not visually obvious in the JSON.

#### Interpretation

(a), (b) and (d) are contradictions between documents and the project's own committed outputs. (c) is
a report of an experiment that was never run.

**INTERPRETATION**: whatever the cause, these are the findings most likely to be fatal in review —
because they are checkable in under a minute by anyone who opens `reports/task12_robustness.json`
next to `README.md`, and because a reviewer who finds one untraceable table will reasonably discount
every other number in the submission.

#### Recommendation

See **R-4** and **R-5** in §13.

---

## 8. Major issues

### 8.1 MAJOR M-1 — A3 ablation EV is a `nanmean` over 15.8% of events, presented as a full-population result

#### Evidence

`src/evaluation/robustness.py:240` — ablation A3 takes the unconstrained global argmax:

```python
a3_actions = [ALL_ACTIONS[int(np.argmax(ev_matrix[i]))] for i in range(N)]
```

`src/data/generate_synthetic.py:218-220` — the oracle stores `NaN` for any action outside the safe
set at generation time:

```python
for a in ALL_ACTIONS:
    oracle_row[f"SYNTHETIC_ORACLE_ONLY_true_p_{a}"]  = true_probs.get(a, np.nan)
    oracle_row[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"] = true_evs.get(a, np.nan)
```

`src/evaluation/robustness.py:260` — those `NaN`s are then silently discarded:

```python
"mean_oracle_ev_inr": float(np.round(np.nanmean(ora_ev_arr), 2)),
```

#### Recomputed (M2)

| Quantity | Value |
| :--- | ---: |
| A3 safety-violation rate (independently reproduced) | **84.21% — 12,632 / 15,000** |
| A3 action mix | `update_information` 97.98%, `switch_method` 1.25%, `retry_later` 0.73%, `retry_now` 0.05% |
| Events A3's published EV actually averages over | **2,368 of 15,000 (15.8%)** |
| Published A3 mean oracle EV (`TASK_12_ROBUSTNESS.md:66`) | ₹2,984.68 |
| Recomputed EV over that same 15.8% subset | ₹3,003.03 |
| **Recomputed A3 EV over all 15,000 events** | **₹2,451.96** |
| Recomputed A2/A4 (gated) EV over all 15,000 events | ₹2,355.03 |

The published ₹2,984.68 is the mean over precisely the events where the *unconstrained* choice
happened to be legal — an extreme survivorship-selected subset — printed in the same table column as
A0/A1/A2/A4, which are means over all 15,000.

#### Interpretation

Two separate points, pulling in opposite directions.

1. **The 84.21% violation rate is real and independently verified.** Its mechanism, however, is not
   the one the documents describe. `README.md:110` explains it as "Unconstrained ML models attempt to
   prompt users for information updates during complete bank downtime because the transaction value
   is high." The actual mechanism is **action-space extrapolation**: `update_information` is only
   ever *logged* in contexts where the safety gate permits it (i.e. `expired_card` /
   `invalid_information`, where the generator grants it a +3.0 logit bonus at
   `src/data/ground_truth.py:89-95`), so the model learns "update_information ⇒ high recovery" and
   extrapolates that association into contexts where the action–context pair was never observed. This
   is a positivity violation, and it is a more interesting finding than the anthropomorphic framing.

2. **The corrected comparison changes the safety-gate story.** Over the full population the
   unconstrained policy is genuinely worth ≈₹97/event *more* in true simulated EV than the gated
   policy. The environment's own economics do not justify the gate: the `misaligned_action` penalty
   is ₹5.00 (`configs/synthetic_config.yaml:35`), far too small to offset the +0.2 base logit the
   generator assigns `update_information` (`src/data/ground_truth.py:30`). **The Safety Gate is a
   compliance constraint imposed from outside the model, not an EV optimization** — a defensible and
   arguably stronger claim than the one currently made, but not the claim currently made.

#### Recommendation

See **R-6** in §13.

---

### 8.2 MAJOR M-2 — Distribution-shift experiments evaluate shifted inputs against unshifted ground truth

#### Evidence

`src/evaluation/robustness.py:284-351`. The shifts are applied to the model's input frame:

```python
df_shifted = df_test_obs.copy()
if amt_mult != 1.0:
    df_shifted["amount"] = df_shifted["amount"] * amt_mult                    # line 289
...
df_shifted["failure_category"] = np.where(mask_soft, "soft_decline", ...)     # line 295
...
df_shifted["payment_method"]   = np.where(mask_upi, "upi_intent", ...)        # line 301
```

But ground truth is read from the **original, unshifted** oracle CSV:

```python
p_true_col = df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_p_{a}"].values        # line 342
ora_ev_matrix[:, a_idx] = (p_true_col * amounts) - c_val - d_vec - f_val      # line 351
```

`src/data/ground_truth.py` makes the true probability an explicit function of exactly the mutated
fields: `failure_category` (lines 35-50), `payment_method` (lines 73-78), and `amount` via the
₹10,000 threshold (lines 82-86). Every shifted row therefore carries ground truth computed for a
context that no longer exists.

#### Recomputed (M2)

Recomputing ground truth correctly for the same shifts, over all 15,000 events:

| Shift | Published ML EV | **Recomputed true ML EV** | Published regret | **Recomputed true regret** |
| :--- | ---: | ---: | ---: | ---: |
| (unshifted reference) | ₹2,349.89 | **₹2,355.03** | ₹1.56 | **₹1.63** |
| `SHIFT_FAILURE_MIX` (60% soft_decline) | ₹2,349.65 | **₹2,658.37** | ₹1.39 | **₹0.53** |
| `SHIFT_TRANSACTION_VALUE` (3.0× amount) | ₹7,078.57 | **₹7,518.24** | ₹4.18 | **₹3.47** |
| `SHIFT_PAYMENT_METHOD_MIX` (70% UPI) | ₹2,349.90 | **₹2,360.44** | ₹1.54 | **₹1.61** |

The ₹309 error on `SHIFT_FAILURE_MIX` is the clearest symptom: the published figure is essentially
unchanged from the unshifted case (₹2,349.65 vs ₹2,349.89) because the oracle side of the computation
never moved.

#### Interpretation

The experiment as implemented does not test distribution robustness — it measures a model operating
in one world against the truth of another. **The conclusion happens to survive** a correct
recomputation (regret stays bounded under all three shifts), so `TASK_12_ROBUSTNESS.md`'s substantive
claim is probably true; but the evidence currently offered for it does not support it, and the
specific numbers published are wrong by up to ₹309/event.

The same stale-ground-truth issue affects the **economic sensitivity** scenarios: `value_multiplier`
scales `amount` (`robustness.py:105`) without recomputing the true probability, even though the
generator's `amount > 10000` interaction depends on it.

#### Recommendation

See **R-9** in §13.

---

### 8.3 MAJOR M-3 — SNIPS variance, effective sample size, and the absent confidence interval

#### Evidence

`src/policy/evaluation.py:146-173`. The estimator is implemented correctly:

```python
ml_matches  = (df_eval["ml_action"].values == logged_actions)
ml_weights  = 1.0 / propensities[ml_matches]
ml_rewards  = realized_logged_rewards[ml_matches]
ml_ips_ev   = float(np.sum(ml_weights * ml_rewards) / N)
ml_snips_ev = float(np.sum(ml_weights * ml_rewards) / np.sum(ml_weights))
ml_ess      = float((np.sum(ml_weights) ** 2) / np.sum(ml_weights ** 2))
```

This is exactly `V_IPS = (1/N)·Σ 1[aᵢ = π(xᵢ)]·rᵢ / e(aᵢ|xᵢ)` and `V_SNIPS = Σ w·r / Σ w` for a
deterministic target policy — the standard forms. The reward is
`recovered_gmv − action_cost − downside_penalty − friction_cost`
(`src/policy/evaluation.py:136-141`), all realized post-decision quantities **of the logged action**,
which is correct for OPE and is **not** leakage into the policy.

No confidence interval, standard error, or variance estimate is computed anywhere in the repository,
and none appears in any report, the README, the dashboard, or either pitch document.

#### Recomputed (M5) — 2,000 bootstrap replicates, seed 0

| Quantity | Point estimate | 95% bootstrap CI | Bootstrap SD | Coverage | Matched n | ESS |
| :--- | ---: | :---: | ---: | ---: | ---: | ---: |
| O1 SNIPS EV | ₹2,425.91 | **[₹2,077.52, ₹2,881.65]** | ±₹207.54 | 38.47% | 5,770 | **1,730.5** |
| O1 IPS EV | ₹2,368.83 | [₹2,001.26, ₹2,835.56] | ±₹214.42 | 38.47% | 5,770 | 1,730.5 |
| Baseline SNIPS EV | ₹1,546.59 | [₹1,462.77, ₹1,628.74] | ±₹42.62 | 72.90% | 10,935 | 5,538.2 |
| **SNIPS uplift** | **₹879.32** | **≈[₹531, ₹1,346]** | — | — | — | — |
| **Direct simulator uplift** | **₹683.29** | (full population, +40.87%) | — | 100% | 15,000 | 15,000 |

Overlap and support diagnostics (M5):

| Diagnostic | Value | Assessment |
| :--- | ---: | :--- |
| Minimum logging propensity | 0.075 | ε/K with ε=0.30, K=4 — bounded away from 0 |
| Maximum importance weight | 13.33 | Bounded; no clipping needed and none applied |
| Distinct propensity values observed | {0.075, 0.10, 0.775, 0.80, 1.0} | Consistent with the ε-greedy design |
| Target-policy actions with zero logging support | **0** | Positivity holds — the target policy is confined to the same safe set the logging policy explores |
| ESS as a fraction of N | **11.5%** | Low |

#### Interpretation — the three values must be distinguished

The audit brief asked for a clear separation of *estimator value*, *true simulated policy value* and
*oracle value*. They are:

| | Value | What it is |
| :--- | ---: | :--- |
| **Estimator value (SNIPS)** | ₹2,425.91 | Off-policy estimate from 38.5% matched episodes, ESS 1,730, 95% CI ±≈₹400 |
| **True simulated policy value** | **₹2,355.03** | Direct ground truth over all 15,000 events — the authoritative number |
| **Oracle value** | ₹2,356.66 | `max` over the safe set with true probabilities — an upper bound by construction |

**The SNIPS estimate exceeding the oracle is not an error and is not evidence of leakage.** It is
ordinary sampling variance on an 11.5%-ESS estimator with heavy-tailed lognormal rewards: the
+₹70.88 excess over the true value is 0.34 bootstrap standard deviations. The direct simulator
resolves the discrepancy completely, and the project's own scratch note
(`scratch/audit_snips_oracle.py`, untracked because `scratch/` is gitignored) reaches the same
conclusion.

**INTERPRETATION**: the estimator is statistically sound but **not precise enough to carry a
headline**. A quantity with roughly ±50% relative uncertainty is currently the README badge, the
dashboard hero metric, and the lead figure in both pitch decks — while the low-variance,
full-population estimate (+₹683.29/event, +40.9%) is computed nowhere and reported nowhere. The
correct framing is: direct simulator as the headline, SNIPS as the supporting off-policy check that
independently corroborates it.

#### Recommendation

See **R-8** in §13.

---

### 8.4 MAJOR M-4 — ROC AUC 0.8532 and Brier 0.1516 are validation-set metrics labelled as test-set results

#### Evidence

`scripts/train_recovery_model.py:36-59` — six candidates are trained, every one is scored on
`val.csv`, the minimum-Brier candidate is selected on `val.csv`, and **those same validation metrics**
are written to the report:

```python
metrics = predictor.evaluate(df_val)          # line 44 — scored on validation
...
if metrics["brier_score"] < best_brier:       # line 49 — selected on validation
...
report_data = {
    "selected_model": best_name,
    "validation_metrics": results[best_name], # line 70 — published
    ...
}
```

No test-set metric is computed anywhere in the pipeline. `reports/task11_model_results.json`
correctly names its field `validation_metrics`.

`TASK_11_RESULTS.md:50-56` then prints those figures under the heading:

> ## 5. Evaluation Results (Test Set: 15,000 Events)
> ### Pillar A: Predictive Model Quality (Observed Actions)
> - **ROC AUC**: `0.8532`

`README.md:122` labels the same number "Model Predictive ROC AUC" with no split qualifier.

#### Recomputed (M3) — the committed model re-scored on all three splits

| Split | ROC AUC | Brier | Log loss | Mean calibration error |
| :--- | ---: | ---: | ---: | ---: |
| Train (70,000) | 0.8623 | 0.1474 | 0.4305 | 0.0196 |
| **Validation (15,000)** — published as "test" | **0.8532** | **0.1516** | **0.4420** | **0.0130** |
| **Test (15,000)** — never reported | **0.8578** | **0.1496** | **0.4366** | **0.0101** |

**RECOMPUTED**: retraining `RecoveryPredictor("hist_gb", calibrate=True)` from scratch reproduces the
validation metrics to four decimal places, so the numbers themselves are correct — only their label
is wrong.

Model configuration verified directly from the loaded artifact:

| Property | Value |
| :--- | :--- |
| Base estimator | `HistGradientBoostingClassifier(max_iter=50, max_depth=6, random_state=42)` |
| Calibration | `CalibratedClassifierCV(method="sigmoid", cv=5)` — **Platt scaling, not isotonic** |
| Calibrated sub-classifiers | 5 |
| Preprocessing | `StandardScaler` on 10 numeric; `OneHotEncoder(handle_unknown="ignore")` on 14 categorical + `action`; `remainder="drop"` |
| Random state | 42, fixed on every candidate |
| Serialization | The whole `RecoveryPredictor` object pickled via `joblib.dump` |

**EVIDENCE**: `TASK_16_REPRODUCTION_AUDIT.md:174` states "HistGradientBoosting + **Isotonic**".
`src/models/recovery_predictor.py:59` specifies `method="sigmoid"`. The prior audit's description of
the calibration method is incorrect.

#### Interpretation

The practical harm is small — the true held-out figures are marginally *better* than the published
ones. But selecting a model on a split and then reporting that split's metrics as held-out
performance is a textbook methodological error, it is one an ML-literate reviewer looks for first,
and it costs nothing to fix.

#### Recommendation

See **R-7** in §13.

---

### 8.5 MAJOR M-5 — Executor accepts replays and does not bind decisions to payments

#### Evidence

`src/agent/executor.py:21-141`. The executor performs five checks — audit record exists, action
matches the approved action, action is in `ALL_ACTIONS`, decision is not `STOP`/`ESCALATE`, action is
in `safe_actions`.

**INTERPRETATION**: this is the right architecture — the executor re-validates independently rather
than trusting the caller or the frontend, which correctly answers the audit question about backend
authority.

Two checks are absent:

- `payment_id` is accepted as a parameter (line 21) and used **only to populate the response** (lines
  36, 49, 62, …). It is never compared against `audit_record["payment_id"]`.
- Nothing reads back `audit_record["execution_status"]`. `update_execution_status` is called after a
  successful execution (line 140), but no check rejects a second attempt.

`src/api/app.py:44-50` — CORS is configured with a wildcard origin *and* credentials:

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
```

`src/api/app.py:174-186` — `GET /audit/{decision_id}` has no authentication dependency and returns the
complete `input_context`. No endpoint in the application has any auth.

`src/agent/audit.py:9-38` — `AuditStore` is an unbounded in-memory `dict` with a lock, no persistence
and no eviction.

#### Recomputed (M4)

| Probe | Result |
| :--- | :--- |
| Execute the same `APPROVED` decision 3× consecutively | **All 3 returned HTTP 200 `scheduled`** with distinct `execution_id`s (`exec_731636c3`, `exec_743a6ac4`, `exec_fe096257`) |
| Execute decision *X* under `payment_id: "pay_SOMEONE_ELSE"` | **HTTP 200 `scheduled`**; the response echoed the substituted payment id |
| `GET /audit/{id}` with no credentials | **HTTP 200**; full `input_context` returned (amount, customer tenure, historical success rate, retry history) |

#### Interpretation

In a real recovery system, the replay result means one approval can dispatch an unbounded number of
retries — precisely the harm the "bounded agent" and retry-cap design exist to prevent. The audit
trail records only the last status, so the replays are not even visible after the fact.

`TASK_13A_BACKEND.md:10` describes this as a "**production-grade** FastAPI REST Service". On the
evidence — no authentication on any endpoint, no idempotency, no decision-to-payment binding,
wildcard CORS with credentials, and a volatile in-memory audit store — that description is not
supportable. **INTERPRETATION**: "prototype service" is accurate and costs the submission nothing;
"production-grade" invites a reviewer to test it.

#### Recommendation

See **R-11** in §13.

---

### 8.6 Additional major findings (recorded for completeness)

Two further issues rise above minor severity and are recorded here.

**M-6 — The evaluated policy is not the deployed policy.**
**EVIDENCE**: every published EV, uplift and regret figure comes from `src/policy/evaluation.py:89-124`,
a pure `argmax` over the safe set. The system actually served by `POST /decide` is
`RecoveryAgent.decide` (`src/agent/recovery_agent.py:111-154`), which adds three stopping rules and a
low-confidence escalation that sets `execution_available: false`.
**RECOMPUTED (M2)**: on the test set, **495 of 15,000 events (3.30%)** fall in the `low` confidence
band and would return `ESCALATE` — the evaluation counts their intervention as taken. The
`NON_POSITIVE_EV` rule fires on **0** events, so it is untested in practice.

**M-7 — The "competent deterministic baseline" is essentially the data-generating policy.**
**EVIDENCE**: `src/policy/baseline.py:15-32` and the heuristic branch of
`src/data/logging_policy.py:29-41` are near-identical, differing only for `upi_timeout` and
`authentication_failure`.
**RECOMPUTED (M2)**: they agree on **87.6%** of test events.
**INTERPRETATION**: the hidden interactions in `src/data/ground_truth.py:52-95` (PSU night
maintenance, UPI peak-hour, cross-border 3DS, the high-amount threshold, stale-info alignment) were
designed specifically to defeat this heuristic. Beating it is close to a property of the generator's
construction rather than an empirical result. This is a fair *methodological demonstration* — it shows
the pipeline can recover known structure — but it is currently presented as a competitive comparison.

---

## 9. Verified strengths

These held up under adversarial inspection and deserve to be stated as firmly as the problems.

### 9.1 VERIFIED — No oracle or outcome leakage reaches the model

**EVIDENCE** — enforcement is structural, not merely nominal:

- `src/models/preprocessing.py:19-51` — `ALL_PREDICTOR_FEATURES` = 10 numeric + 14 categorical +
  `action` = **25 columns**. All 24 context features are pre-decision quantities.
- `src/models/preprocessing.py:67-80` — `prepare_feature_dataframe` selects that list **explicitly by
  name**; no wildcard, no `drop`-based exclusion.
- `src/models/preprocessing.py:58-64` — the `ColumnTransformer` uses `remainder="drop"`, so additional
  columns present in the frame cannot reach the estimator even accidentally.

**RECOMPUTED (M1)** — targeted grep for every field named in the audit brief across `src/`, `scripts/`
and `frontend/src/`:

| Field | Appears in a training / inference / API-decision path? |
| :--- | :--- |
| `recovered` | No — only as the `target_col`, and in the generator and validation module |
| `recovery_timestamp` | No — generator only |
| `time_to_recovery_hours` | No — generator only |
| `recovered_gmv` | No — generator, and as an OPE *reward* component at `evaluation.py:137` |
| `action_cost`, `downside_penalty`, `friction_cost` | No — as OPE reward components only; the *functions* of the same name are decision-time cost lookups, which is correct |
| `true_recovery_probability` | No — oracle CSV column, read only by `validation.py` and `evaluation.py` |
| `SYNTHETIC_ORACLE_ONLY_*` | **Only** in `src/policy/evaluation.py` and `src/evaluation/robustness.py` — never in training, the advisor, the agent, or any API response |

**INTERPRETATION**: `action` is legitimately available at decision time — it is the decision variable
being scored, and `predict_proba_all_actions` evaluates every candidate counterfactually, which is the
correct construction for `P(recovery | X, a)`. The action-dependent economic quantities `C(a)`, `D(a)`
and `F(a)` are design parameters known before acting, not outcomes. **No action-dependent variable
smuggles in outcome information.**

### 9.2 VERIFIED — The ground-truth simulator is genuinely separated from the learned model

**EVIDENCE** — `compute_true_recovery_probability` (`src/data/ground_truth.py:11`) is imported by
exactly three modules: the generator, `src/evaluation/robustness.py` (where it is imported but never
called — see C-3c), and this audit's own recomputation. It is **not** imported by
`src/policy/advisor.py`, `src/agent/recovery_agent.py`, `src/api/app.py`, or
`src/models/recovery_predictor.py`.

**EVIDENCE** — ordering in `src/policy/evaluation.py`: actions are selected at lines 89-124 from model
predictions and the safety mask alone; the oracle is opened at line 180, **after** selection. The
oracle cannot influence the decision.

### 9.3 VERIFIED — Deterministic, bit-exact dataset reproduction

**RECOMPUTED (M3)** — `generate_dataset("configs/synthetic_config.yaml")` was re-run into a scratch
directory outside the repository and SHA-256-compared against `data/synthetic/checksums.json`:

| File | SHA-256 |
| :--- | :--- |
| `train.csv` | **IDENTICAL** |
| `train_oracle.csv` | **IDENTICAL** |
| `val.csv` | **IDENTICAL** |
| `val_oracle.csv` | **IDENTICAL** |
| `test.csv` | **IDENTICAL** |
| `test_oracle.csv` | **IDENTICAL** |

**EVIDENCE** — seed handling is correct: a single `np.random.RandomState(seed)`
(`generate_synthetic.py:62`) is threaded through vectorized feature sampling, the logging policy
(`select_logged_action(..., rng=rng)`), and outcome sampling (`sample_recovery_outcome(..., rng=rng)`).
No unseeded `np.random` call exists in the generation path.

### 9.4 VERIFIED — Model retraining reproducibility

**RECOMPUTED (M3)** — retraining the selected candidate from `train.csv` reproduced the committed
artifact's validation metrics exactly:

```
Retrained : {'roc_auc': 0.8532, 'log_loss': 0.442, 'brier_score': 0.1516, 'mean_calibration_error': 0.013}
Committed : {'roc_auc': 0.8532, 'log_loss': 0.442, 'brier_score': 0.1516, 'mean_calibration_error': 0.013}
```

Re-running `run_policy_evaluation()` against the committed model and data reproduced
`reports/task11_policy_evaluation.json` **field-for-field**, confirming the pipeline is deterministic
and that the committed reports were genuinely produced by the committed code. (The figures inside them
are nonetheless affected by C-1.)

### 9.5 VERIFIED — Correct SNIPS mathematics with genuine action support

**EVIDENCE + RECOMPUTED (M1, M5)** — derived in full in §8.3. The estimator matches its textbook
definition; overlap is real rather than assumed (minimum propensity 0.075, maximum weight 13.33, zero
target-policy actions without logging support); no clipping is required and none is applied; ESS is
computed and reported.

**INTERPRETATION**: the implementation is correct. The concern in §8.3 is about precision and
presentation, not correctness.

### 9.6 VERIFIED — Per-event regret is non-negative across the entire population

**RECOMPUTED (M2)** — computing `regretᵢ = max_{a∈A_safe(Xᵢ)} EV_true(Xᵢ,a) − EV_true(Xᵢ, π(Xᵢ))` for
every one of the 15,000 test events:

| Measurement | Value |
| :--- | ---: |
| Events with `regretᵢ < 0` | **0** |
| Minimum per-event regret | 0.000000 |
| Maximum per-event regret | ₹1,616.76 |
| Mean per-event regret | **₹1.63** |
| Events where O1's action equals the oracle's best action | **97.99%** |
| Safety-gate recomputation mismatches vs stored `safe_actions` | **0 / 15,000** |

**INTERPRETATION**: the theoretical property `EV_true(π) ≤ EV_true(oracle)` genuinely holds per-event.
`TASK_16_REPRODUCTION_AUDIT.md:126` claims it "holds perfectly across 100% of test episodes" — the
claim is true, but **the repository never computes it**; the code compares two aggregate means (see
C-1). The prior audit asserted a property it did not test.

### 9.7 VERIFIED — Consistent TIER C synthetic disclosure

**EVIDENCE** — TIER C disclosure appears in `README.md:199`, `TASK_11_RESULTS.md:65,101`,
`TASK_12_ROBUSTNESS.md:112`, `TASK_13A_BACKEND.md:168`, `TASK_13B_DASHBOARD.md:137`,
`TASK_14_E2E_VALIDATION.md:89`, and as a persistent visual footer on both the Overview
(`Overview.tsx:180-186`) and Evaluation (`Evaluation.tsx:186-193`) dashboard views. The `/health`
endpoint returns `"data_tier": "TIER C — Synthetic Evaluation Environment"`.

`TASK_15_SUBMISSION_PACKAGE.md:43-44` explicitly forbids the overclaiming formulation:

> - ❌ *"Recovered 56.8% more Razorpay revenue"*
> - ✅ *"Achieved 56.8% higher synthetic estimated economic value … under our evaluation environment."*

**INTERPRETATION**: this is the strongest part of the documentation. **No instance of a synthetic
result being described as a Razorpay production result was found anywhere in the repository.** The
single unsourced quantitative claim located is `docs/PITCH_5_MINUTES.md:33` — "merchants lose millions
in recoverable GMV" — a market assertion with no citation.

### 9.8 VERIFIED — Determinism, and no scientific logic duplicated in the frontend

**RECOMPUTED (M2, M4)** — `PolicyAdvisor.recommend` and the vectorized evaluation path selected
identical actions on **800 / 800** sampled events. Repeated `evaluate_safety_gate` calls on the same
context are byte-identical.

**EVIDENCE (M1)** — the React components perform no EV arithmetic, no safety filtering and no action
selection; they render backend response fields. `frontend/src/types/api.ts` contains no oracle field.
`fetchDecision` / `executeAction` / `fetchAudit` map one-to-one onto real backend endpoints. Execution
remains simulated throughout (`SimulatedRecoveryExecutor` performs no network call to any gateway).

**EVIDENCE** — 53 / 53 tests pass across 8 suites, matching the README claim.

---

## 10. Corrected headline figures

**RECOMPUTED (M2, M5)** — all values below were derived independently over the complete 15,000-event
test population, using `src/data/ground_truth.py` and `src/data/economics.py` directly rather than the
committed `*_oracle.csv` files (which are affected by C-1).

| Figure | Published | **Corrected (this audit)** | Method |
| :--- | ---: | ---: | :--- |
| Direct true O1 policy EV | ₹2,349.72 | **₹2,355.03** | M2 |
| Direct true oracle best EV | ₹2,350.67 | **₹2,356.66** | M2 |
| Direct true baseline EV | ₹1,668.04 | **₹1,671.74** | M2 |
| **Corrected regret** | ₹0.94 / event | **₹1.63 / event** | M2 |
| **Corrected policy efficiency** | 99.96% | **99.93%** | M2 |
| **Corrected direct uplift over baseline** | (not published) | **₹683.29 / event (+40.87%)** | M2 |
| SNIPS O1 EV | ₹2,425.91 | ₹2,425.91 *(unchanged — reproduces exactly)* | M3 |
| SNIPS baseline EV | ₹1,546.59 | ₹1,546.59 *(unchanged)* | M3 |
| SNIPS ESS | 1,730.5 | 1,730.5 *(unchanged)* | M3 |
| **SNIPS 95% CI — O1 EV** | not reported | **[₹2,077.52, ₹2,881.65]** | M5 |
| **SNIPS 95% CI — uplift** | not reported | **≈[₹531, ₹1,346]** | M5 |
| A3 (no safety gate) EV | ₹2,984.68 | **₹2,451.96** (full population) | M2 |
| A3 safety-violation rate | 84.21% | **84.21%** *(unchanged — verified)* | M2 |
| Model ROC AUC — **test** split | not reported | **0.8578** | M3 |
| Model Brier — **test** split | not reported | **0.1496** | M3 |

### 10.1 Discrepancy note — this audit did **not** silently reconcile a figure in its brief

The Task 16A-1 brief specified *"Direct O1 true EV: approximately ₹2,349.04"*.

**This audit measured ₹2,355.03, not ₹2,349.04, and is recording the divergence rather than adopting
the brief's number.**

The brief's figure is reconstructible as `₹2,350.67 − ₹1.63` — that is, the **uncorrected** published
oracle EV minus the **corrected** regret. That subtraction mixes a figure computed on the contaminated
oracle population with a figure computed on the correct one, so it does not correspond to any single
measurement. The internally consistent corrected set is:

```
Direct true O1 EV      = ₹2,355.03
Direct true oracle EV  = ₹2,356.66
Direct true regret     = ₹2,356.66 − ₹2,355.03  =  ₹1.63 / event
Policy efficiency      = 2355.03 / 2356.66      =  99.93%
Direct uplift          = ₹2,355.03 − ₹1,671.74  =  ₹683.29 / event  (+40.87%)
```

Both the regret (₹1.63) and the efficiency (99.93%) requested in the brief are confirmed by this
audit; only the absolute EV *levels* differ, and they differ because C-1 shifts **both** the O1 and
the oracle levels by approximately ₹5–6 in the same direction, leaving their difference far less
affected than either level.

**Cross-check** — the project's own Task 12 code path, which deduplicates the oracle before merging,
independently reports `ml_policy_ev_ci.mean = ₹2,349.89`, `oracle_best_ev_ci.mean = ₹2,350.91` and
`regret_ci.mean = ₹1.56` for the identical experiment. Those figures still exclude the 114 test events
that have no oracle row at all, which accounts for the remaining ≈₹5 gap against this audit's
full-population recomputation.

All three sets of numbers are reported here rather than averaged, reconciled, or silently replaced.

---

## 11. Test audit

**INTERPRETATION** — the suite confirms the happy path and the static feature list. **Not one of the
53 tests would fail on C-1, C-2, C-3, M-1 or M-2.**

| Suite | What it proves | What it does **not** prove |
| :--- | :--- | :--- |
| `test_generator.py` | Safety gate returns `["do_nothing"]` for `hard_decline` and for `retry_count >= 3`; expired-card restriction; logging policy explores ≥3 actions with non-zero propensity; `EV` arithmetic on one hand-checked case (497.0) | Nothing about unrecognized categories — the exact hole in C-2. The EV assertion is a single hardcoded expected value that merely reproduces the implementation's own constants. |
| `test_anti_circularity.py` | That the **generator** produces action overlap, stochastic outcomes, a hidden signal, and an oracle that beats the baseline | Nothing about the **committed** dataset — it regenerates 5,000 fresh events. Criterion 4 ("ML model receives ZERO oracle variables") delegates to `validation.py:117-122`, which only greps *column names in the observed CSV* for `"ORACLE"`, `"true"`, `"best"`. **It would pass unchanged if `recovered_gmv` were added to `ALL_PREDICTOR_FEATURES`.** The headline anti-circularity test does not test the actual leakage vector. `test7_ml_learnability` computes AUC **in-sample** on its own training data. |
| `test_task11_policy.py` | Probabilities in [0,1]; recommended action inside `A_safe`; `hard_decline` forces `do_nothing`; action changes prediction; retry cap forces `do_nothing` | The two leakage tests are static assertions over a constant list — they can only fail if someone edits that constant. `test_7` checks column **count**, not identity. `test_10` asserts only that ESS > 0. |
| `test_task12_robustness.py` | Ablation yields 5 variants and A3 violates; shifts run without retraining; test timestamps exceed train timestamps | **`test_10` asserts `ranking_stable is True` and passes only because `setUpClass` builds a sanitized fixture** — `drop_duplicates("event_id")` plus an `inner` merge on 500 rows, which eliminates the `NaN`s. The production run of the same code emits `false`. This is a test that passes while the pipeline it guards is broken, and it is the clearest single symptom of C-1. |
| `test_task13_agent.py` | Bounded action; audit record written; `MAX_ATTEMPTS_EXCEEDED` forces `do_nothing`; explanation is a non-trivial string | No test of the `UNSAFE_ACTION` or `NON_POSITIVE_EV` stopping rules; no determinism test; `test_4` asserts only `len(reason) > 20`. |
| `test_task13_executor.py` | Approved action executes; mismatched action, `STOP`, `ESCALATE` and unknown decision id are all rejected | No replay / idempotency test; no `payment_id` binding test — both fail in practice (M-5). |
| `test_task13_api.py` | HTTP 422 on malformed input; HTTP 404 on missing audit record; decision response shape | `test_execute_and_audit_flow` asserts `status_code in [200, 400]` — it accepts success and failure equally and therefore proves nothing about execution behaviour. |
| `test_task14_e2e.py` | Six genuine end-to-end paths including safety-gate blocking, `STOP` rejection at the executor, and an assertion that no oracle key appears in decision or audit payloads | The strongest suite, but contains no adversarial input case: no unknown category, no replay, no identifier substitution. |

---

## 12. Reproducibility

**INTERPRETATION**: reproducibility is strong **if you already know the undocumented steps**, and
impossible from the documentation alone.

| Stage | Status | Note |
| :--- | :--- | :--- |
| Dataset | **VERIFIED** | 6/6 SHA-256 digests identical after regeneration (§9.3) |
| Model | **VERIFIED** | Retraining reproduces all four validation metrics exactly (§9.4) |
| Evaluation reports | **VERIFIED** | `task11_policy_evaluation.json` reproduces field-for-field |
| Documented metrics | **INCORRECT** | The README robustness matrix and `TASK_11_RESULTS.md §6` reproduce from no committed artifact (C-3) |
| Clean clone | **FAILS** | See below |

**EVIDENCE — a fresh clone cannot run anything.**

- `.gitignore` excludes `data/synthetic/*.csv` and `models/*.joblib`. Neither the dataset nor the model
  is in the repository.
- `README.md:160-190` (Quick Start) goes directly from dependency installation to
  `uvicorn src.api.app:app`. It contains no data-generation step and no training step.
- `scripts/train_recovery_model.py` is referenced in **no document** except
  `TASK_16_REPRODUCTION_AUDIT.md`.
- `SYNTHETIC_GENERATION.md:121` does document the generation command — but `docs/DEMO.md`,
  `scripts/demo_full_stack.md` and the README do not reference it.
- Consequence: on a clean clone, `POST /decide` raises on the missing joblib, `GET /events` returns
  HTTP 404, `scripts/demo_agent.py` fails, and the test suite cannot even collect
  (`test_task11_policy.py` reads `data/synthetic/train.csv` at class setup; `test_task12_robustness.py`
  loads `models/recovery_predictor.joblib`). **The "53/53 tests passed" claim is unreachable from a
  fresh checkout.**
- `frontend/.env.example` is untracked — caught by the `.env.*` pattern in `.gitignore`.
- `requirements.txt` pins nothing (§4).

---

## 13. REQUIRED CORRECTIONS BEFORE BUILDATHON SUBMISSION

**RECOMMENDATION** — in priority order. **None of these was applied. This audit modified no code, test,
dataset, report or document.**

### Priority 1 — Must fix (a reviewer will find these)

**R-1 — Make `event_id` unique and assert alignment.**
Replace `rng.randint` at `src/data/generate_synthetic.py:94` with a collision-free identifier
(`f"evt_{i:08d}"`, or draw without replacement). Add a post-generation assertion before splitting:

```python
assert df_obs.event_id.is_unique
assert (df_obs.event_id.values == df_oracle.event_id.values).all()
```

Regenerate the dataset and `data/synthetic/checksums.json`. *(Fixes C-1 at source; also removes the
`NaN`s that cause C-3d.)*

**R-2 — Fix the oracle join and compute both means from the same frame.**
At `src/policy/evaluation.py:180`, use
`df_eval.merge(df_test_oracle.drop_duplicates("event_id"), on="event_id", how="left", validate="one_to_one")`,
and compute **both** `mean_oracle_best_ev` and `mean_oracle_ml_ev` from that merged frame rather than
one from the merge and one from the raw CSV. Add `assert merged[...].notna().all()`. Then republish
regret as **₹1.63/event** and efficiency as **99.93%** everywhere they appear — `reports/`,
`README.md`, `TASK_11_RESULTS.md`, `TASK_16_REPRODUCTION_AUDIT.md`,
`frontend/src/components/Evaluation.tsx`, `docs/PITCH_5_MINUTES.md`, `docs/PITCH_SLIDES.md`.

**R-3 — Make the Safety Gate fail closed.**
Define the taxonomy as an `Enum`; constrain `FailedPaymentEvent.failure_category` and `payment_method`
to it so unknown values are rejected with HTTP 422; and add a terminal branch to
`evaluate_safety_gate`:

```python
if cat not in FAILURE_TAXONOMY:
    return ["do_nothing"], ["HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY"]
```

Add a regression test for each of the four rows in the C-2 probe table. Then soften `README.md:112`
from "0.00% across all operations" to "0.00% across the 15,000-event synthetic test set".

**R-4 — Remove or regenerate every untraceable number.**

- `TASK_11_RESULTS.md §6` — replace the action-distribution table with the values in
  `reports/task11_policy_evaluation.json`.
- `frontend/src/components/Overview.tsx:9-15` — same.
- `README.md:140-146` and `frontend/src/components/Evaluation.tsx:145-177` — replace the robustness
  matrix with values read from `reports/task12_robustness.json`, and correct the "High Retry Cost
  (2.5x)" label to 2.0x.
- `TASK_12_ROBUSTNESS.md §4` — **delete it**, or implement the experiment by threading
  `interaction_scale` through `compute_true_recovery_probability` and adding a fifth phase to
  `scripts/run_robustness.py` that writes a `ground_truth_robustness` key.
- `TASK_12_ROBUSTNESS.md §2` — remove the ground-truth phase from the experiment diagram if the phase
  is not implemented.

**R-5 — Fix `ranking_stable` and stop asserting "STABLE" against it.**
Change `np.mean` to `np.nanmean` at `src/evaluation/robustness.py:170`. Regenerate
`reports/task12_robustness.json`. Have the README and dashboard render whatever the JSON says rather
than a hardcoded label.

**R-6 — Report ablation A3 honestly.**
Compute each ablation's EV over the full population by calling `compute_true_recovery_probability` on
the variant's chosen action, rather than indexing a `NaN`-holed oracle matrix. Publish **₹2,451.96**
for A3 and reframe the finding: the Safety Gate costs ≈₹97/event of simulated EV and is a **compliance
constraint, not an EV optimization**. Correct the mechanism description at `README.md:110` from
anthropomorphic framing to action-space extrapolation / positivity violation.

### Priority 2 — Should fix (methodological credibility)

**R-7 — Report test-set model metrics.**
Add `predictor.evaluate(df_test)` to `scripts/train_recovery_model.py` and write both
`validation_metrics` (selection) and `test_metrics` (held-out) to `reports/task11_model_results.json`.
Publish **ROC AUC 0.8578 / Brier 0.1496** as the headline model quality, and label 0.8532 / 0.1516
explicitly as the validation metrics used for selection. Correct the "Evaluation Results (Test Set:
15,000 Events)" heading at `TASK_11_RESULTS.md:50`.

**R-8 — Publish uncertainty, and promote the direct estimate to the headline.**
Add bootstrap CIs to every SNIPS figure in `src/policy/evaluation.py`. Make the direct-simulator
uplift (**+₹683.29/event, +40.9%**) the headline in the README badge, the dashboard hero and both pitch
decks, with SNIPS (**₹2,425.91, 95% CI [₹2,077.52, ₹2,881.65], ESS 1,730/15,000**) presented as the
supporting off-policy corroboration. State the estimator / true-value / oracle distinction explicitly
in `TASK_11_RESULTS.md`.

**R-9 — Recompute ground truth inside the shift and sensitivity experiments.**
In `run_distribution_shifts` and `run_economic_sensitivity`, call `compute_true_recovery_probability`
on the **shifted** contexts instead of reading `SYNTHETIC_ORACLE_ONLY_true_p_{a}` from the unshifted
CSV. Republish the shift table, noting that the qualitative conclusion survives but the numbers change
by up to ₹309/event.

**R-10 — Evaluate the policy that is actually deployed.**
Either run `RecoveryAgent.decide` inside the evaluation loop, or report the ESCALATE rate (3.30%, 495
events) alongside every policy value so the two describe the same system.

**R-11 — Harden the executor and the API; retitle the service.**
Verify `payment_id` against `audit_record["payment_id"]`; reject any decision whose
`execution_status != "pending"`; add an API-key or bearer dependency to `/decide`, `/execute` and
`/audit`; narrow CORS to the dashboard origin and drop either `allow_credentials` or the wildcard.
Replace "production-grade" at `TASK_13A_BACKEND.md:10` with "prototype".

**R-12 — Make a clean clone runnable.**
Add the two missing steps to the README Quick Start —
`python src/data/generate_synthetic.py --config configs/synthetic_config.yaml --events 100000 --outdir data/synthetic`
then `python scripts/train_recovery_model.py` — before the `uvicorn` step, and mirror them in
`docs/DEMO.md` and `scripts/demo_full_stack.md`. Un-ignore `frontend/.env.example`.

**R-13 — State the environment's limitations where results are presented.**
Add to the Limitations sections: (a) the deterministic baseline reproduces the data-generating
heuristic on 87.6% of events; (b) every hidden interaction is a deterministic function of features the
model already receives, so there is no unobserved confounding and near-oracle efficiency is
substantially a property of the environment's design; (c) the "temporal" split carries no temporal
structure — timestamps are drawn i.i.d. at `generate_synthetic.py:73` and then sorted, making it
statistically equivalent to a random split, so `DATASET_CARD.md:24`'s "Temporal off-policy evaluation"
overstates what is tested.

### Priority 3 — Worth doing

**R-14** — Strengthen `validation.py`'s `test9_no_feature_leakage` to assert on
`ALL_PREDICTOR_FEATURES` and on the fitted `ColumnTransformer`'s column list, not on CSV header
strings.

**R-15** — Add a per-event assertion `regretᵢ ≥ 0` across all 15,000 events — the property
`TASK_16_REPRODUCTION_AUDIT.md:126` claims to have proven but never computed.

**R-16** — Fix the `assertIn(status_code, [200, 400])` assertion in `test_task13_api.py`; add
adversarial cases for unknown category, replay and identifier substitution.

**R-17** — Remove the stray `font-mono` text rendering literally at
`frontend/src/components/Evaluation.tsx:167`; wire the Evaluation view to `GET /reports/summary`
(currently defined at `services/api.ts:55` and never called) so displayed metrics cannot drift again.

**R-18** — Pin exact versions in `requirements.txt`; record the training scikit-learn version alongside
the joblib.

**R-19** — Either drop the `currency` field or convert USD amounts: 10.36% of events carry
`currency: "USD"` while `amount` is used directly as V against rupee-denominated costs and all output
is labelled "INR".

**R-20** — Read `bootstrap_resamples` from `configs/robustness_config.yaml:5` (currently hardcoded to
200 at `robustness.py:26`; the config says 1000) or delete the key; and vary the bootstrap seed per
call, since a fixed `seed=42` makes every scenario's CI use identical resample indices.

**R-21** — Correct the factual errors in `TASK_16_REPRODUCTION_AUDIT.md`: ε is 0.30, not 0.20;
calibration is sigmoid/Platt, not isotonic; matched events number 5,770, not 5,775; there are 4
distribution shifts, not 3; and the per-episode inequality it reports as verified is never computed by
the code.

**R-22** — Cite or remove "merchants lose millions in recoverable GMV" (`docs/PITCH_5_MINUTES.md:33`).

**R-23** — Correct the `safe` flag semantics at `src/agent/recovery_agent.py:166, 189`: a decision
stopped by `NON_POSITIVE_EV` or `UNSAFE_ACTION` emits `do_nothing`, which is safe, yet is recorded as
`safe: false`.

---

## 14. Audit provenance

| Field | Value |
| :--- | :--- |
| Audit identifier | Task 16A — Independent Scientific Audit |
| Conducted on | 2026-09-02 |
| Commit audited | `156a4cc` |
| Branch audited | `audit/task16a-independent-scientific` |
| Working tree at audit start | clean |
| Files modified by this audit | **none** — this document is the only artifact created |
| Prior reports relied upon | **none** — all prior task reports were treated as unverified claims |
| Verdict | **NEEDS CORRECTION** |

> **Synthetic environment disclosure.** Every figure in this document — published, recomputed, or
> corrected — describes the project's synthetic evaluation environment. None of them is a measurement
> of Razorpay production performance, real customer recovery probabilities, or real money movement,
> and none should be presented as such.
