# DATASET CARD: Payment Recovery Synthetic Dataset

## Dataset Purpose
This synthetic dataset provides a reproducible, non-circular experimental environment for training, validating, and evaluating **Payment Recovery** (Built for Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery).

It enables:
1. Deterministic decline-code baseline evaluation.
2. Machine learning estimation of recovery probability $P(\text{recovery} | X, \text{action})$.
3. Expected Economic Value ($EV$) policy selection under hard safety constraints.
4. Temporal off-policy evaluation across train, validation, and test splits.

---

## Data Origin & Tier Declaration
- **Data Tier**: **TIER C — Public structural data + synthetic recovery environment**.
- **Structural Inspiration**: Transaction schemas, webhook structures, and payment failure fields are structurally aligned with public Razorpay API documentation.
- **Action & Outcome Labels**: Historically logged actions, probabilistic recovery outcomes, recovery timestamps, and economic parameters are **synthetic modeled assumptions**.
- **No Real Claims**: This dataset does NOT contain real Razorpay customer or payment data. All performance metrics represent simulated evidence only.

---

## Dataset Scale & Splits
- **Total Failure Events**: 100,000 episodes
- **Temporal Splitting**: Chronological 70% Train / 15% Validation / 15% Test split based on `failure_timestamp` (Date range: June 1, 2026 to August 30, 2026). Observed and hidden-oracle rows are reordered with the same positional permutation and asserted to be in exact one-to-one correspondence before and after splitting.

> **Interpretation caveat.** Timestamps are drawn i.i.d. from the window and then sorted, so
> the generating distribution does not change over time. The chronological split is therefore
> statistically equivalent to a random split: it guarantees no episode-level overlap between
> splits, but it does **not** test temporal drift or seasonality.

| Split | Event Count | Date Range | File Name |
| :--- | :--- | :--- | :--- |
| **Train** | 70,000 | 2026-06-01 to 2026-08-03 | [`data/synthetic/train.csv`](data/synthetic/train.csv) |
| **Validation** | 15,000 | 2026-08-03 to 2026-08-17 | [`data/synthetic/val.csv`](data/synthetic/val.csv) |
| **Test** | 15,000 | 2026-08-17 to 2026-08-30 | [`data/synthetic/test.csv`](data/synthetic/test.csv) |

---

## Feature Schema

### 1. Identity & Order Context
- `event_id`: Unique synthetic episode ID (`evt_00000000` .. `evt_00099999`), assigned sequentially so it is collision-free by construction. It is the join key between the observed and oracle frames and is **not** a model feature.
- `order_id`: Synthetic order ID (`ord_...`)
- `customer_id`: Synthetic customer ID (`cust_...`)
- `failure_timestamp`: Timestamp of initial failure event (`YYYY-MM-DD HH:MM:SS`)

### 2. Transaction Features
- `amount`: Payment value in currency (range: ₹10.00 – ₹500,000.00, median ₹1,800.00)
- `currency`: Transaction currency (`INR`, `USD`)
- `product_category`: Segment (`electronics`, `apparel`, `saas_subscription`, `digital_goods`, `travel`, `food_delivery`)
- `is_subscription`: Boolean indicator for recurring billing
- `order_value_tier`: Categorical (`low`, `medium`, `high`, `enterprise`)

### 3. Payment Method & Issuer Features
- `payment_method`: Payment instrument (`card_credit`, `card_debit`, `upi_intent`, `upi_collect`, `netbanking`)
- `issuer_category`: Bank type (`psu_bank`, `private_bank`, `foreign_bank`, `neobank`)
- `card_network`: Network scheme (`visa`, `mastercard`, `rupay`, `amex`, `none`)
- `corridor`: Geographical route (`domestic_in`, `cross_border_in_us`, `cross_border_in_eu`, `cross_border_in_sg`)

### 4. Failure Taxonomy Features
- `failure_category`: 13 distinct failure types (`hard_decline`, `soft_decline`, `insufficient_funds`, `expired_card`, `invalid_information`, `issuer_unavailable`, `network_timeout`, `authentication_failure`, `velocity_limit`, `blocked_instrument`, `upi_timeout`, `upi_decline`, `bank_unavailable`)
- `failure_code`: Granular error code (e.g. `BAD_REQUEST_PAYMENT_TIMED_OUT`, `INSUFFICIENT_FUNDS`)
- `error_source`: Origin of error (`issuer`, `gateway`, `customer`, `network`)
- `error_step`: Pipeline step (`authentication`, `authorization`, `payment_initiation`)

### 5. Customer History & Temporal Features
- `customer_tenure_days`: Days since account creation (1 to 1,000)
- `historical_success_rate`: Customer historical authorization rate (0.0 to 1.0)
- `historical_failed_attempts`: Count of past failed attempts
- `historical_retry_count`: Count of past retries across episodes
- `time_since_last_success_hours`: Hours since customer's last successful transaction
- `retry_count_before_event`: Retries already attempted for *this* transaction (0, 1, 2, 3)
- `hour`: Hour of day (0 to 23)
- `day_of_week`: Day of week (0 = Monday, 6 = Sunday)
- `is_weekend`: Binary flag (0 or 1)

### 6. Merchant Features
- `merchant_segment`: Merchant vertical (`e_commerce`, `saas`, `gaming`, `travel_hospitality`, `retail`)
- `merchant_category`: Internal category grouping

### 7. Safety Gate Output
- `safe_actions`: Pipe-separated string of allowable actions (e.g. `retry_now|retry_later|switch_method|do_nothing`)
- `safety_constraints_applied`: Applied hard safety rule tags

### 8. Logged Action & Outcome
- `logged_action`: Historically executed recovery action (`retry_now`, `retry_later`, `switch_method`, `update_information`, `do_nothing`)
- `logging_probability`: Historical policy propensity score $P_{\text{logged}}(a|X)$
- `recovered`: Binary recovery outcome (1 = recovered, 0 = failed)
- `recovery_timestamp`: Timestamp of successful recovery (within 72-hour window)
- `time_to_recovery_hours`: Time elapsed from failure to recovery
- `recovered_gmv`: Recovered transaction amount (equal to `amount` if recovered, else 0.0)

### 9. Action Economics (Modeled Assumptions)
- `action_cost`: Direct cost $C(a)$ in INR
- `downside_penalty`: Downside risk cost $D(a)$ in INR
- `friction_cost`: Customer friction cost $F(a)$ in INR

---

## Action Space (5 Bounded Actions)
1. `retry_now`: Immediate automated payment retry.
2. `retry_later`: Scheduled delayed retry (e.g., +4 hours).
3. `switch_method`: Prompt customer/system to switch payment method (e.g. Card $\rightarrow$ UPI).
4. `update_information`: Prompt customer to update expired/invalid details (e.g. CVV, Expiry).
5. `do_nothing`: Abandon further recovery attempts (zero cost, zero friction).

---

## Oracle Evaluation Dataset (`*_oracle.csv`)
> [!IMPORTANT]
> Oracle files are stored separately (`train_oracle.csv`, `val_oracle.csv`, `test_oracle.csv`) and tagged with `SYNTHETIC_ORACLE_ONLY_`.
> **THESE COLUMNS ARE STRICTLY EXCLUDED FROM ML MODEL INPUTS.** They exist solely for policy regret evaluation, baseline verification, and synthetic environment diagnostics.

Columns include:
- `SYNTHETIC_ORACLE_ONLY_true_recovery_probability_logged`: Hidden true $P(\text{recovery} | X, a_{\text{logged}})$
- `SYNTHETIC_ORACLE_ONLY_true_best_action`: Optimal action maximizing true $EV$
- `SYNTHETIC_ORACLE_ONLY_true_best_ev`: Optimal expected economic value in INR
- `SYNTHETIC_ORACLE_ONLY_baseline_action`: Action selected by competent deterministic baseline
- `SYNTHETIC_ORACLE_ONLY_baseline_ev`: Expected economic value of baseline action in INR
- `SYNTHETIC_ORACLE_ONLY_true_p_{action}`: True probabilities for all actions
- `SYNTHETIC_ORACLE_ONLY_true_ev_{action}`: True EV for all actions

---

## Limitations & Disclaimers
1. **Not Production Data**: This dataset is entirely synthetic.
2. **Modeled Economics**: Action costs, downside penalties, and customer friction values are assumptions designed for decision layer architecture evaluation. They do NOT reflect Razorpay's actual fee structures.
3. **Simulated Uplift**: Any recovery performance or economic uplift demonstrated using this dataset is simulated and serves as proof-of-concept for the decision architecture.
