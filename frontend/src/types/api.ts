export interface FailedPaymentEvent {
  payment_id: string;
  amount: number;
  currency: string;
  product_category: string;
  is_subscription: number;
  order_value_tier: string;
  payment_method: string;
  issuer_category: string;
  card_network: string;
  failure_code: string;
  failure_category: string;
  error_source: string;
  error_step: string;
  corridor: string;
  merchant_segment: string;
  merchant_category: string;
  customer_tenure_days: number;
  historical_success_rate: number;
  historical_failed_attempts: number;
  historical_retry_count: number;
  time_since_last_success_hours: number;
  retry_count_before_event: number;
  hour: number;
  day_of_week: number;
  is_weekend: number;
  logged_action?: string;
  failure_timestamp?: string;
}

export interface RecoveryDecisionResponse {
  decision_id: string;
  payment_id: string;
  action: 'retry_now' | 'retry_later' | 'switch_method' | 'update_information' | 'do_nothing';
  confidence: 'high' | 'medium' | 'low';
  recovery_probability: number;
  expected_value: number;
  safe: boolean;
  safety_rule: string;
  reason: string;
  status: 'APPROVED' | 'ESCALATE' | 'STOP';
  stopping_rule: string | null;
  timestamp: string;
  execution_available: boolean;
}

export interface ExecutionRequest {
  decision_id: string;
  payment_id: string;
  action: string;
}

export interface ExecutionResponse {
  execution_id: string;
  decision_id: string;
  payment_id: string;
  action: string;
  status: 'executed' | 'scheduled' | 'stopped' | 'escalated' | 'rejected';
  message: string;
  timestamp: string;
}

export interface AuditRecordResponse {
  decision_id: string;
  timestamp: string;
  payment_id: string;
  input_context: Record<string, any>;
  candidate_actions: string[];
  safe_actions: string[];
  predicted_probabilities: Record<string, number>;
  expected_values: Record<string, number>;
  selected_action: string;
  confidence: string;
  recovery_probability: number;
  expected_value: number;
  safe: boolean;
  safety_rule: string;
  reason: string;
  status: string;
  stopping_rule: string | null;
  execution_status: string;
}

// Mirrors the generated evaluation artifacts served by GET /reports/summary
// (reports/task11_policy_evaluation.json + reports/task12_robustness.json).
// The dashboard renders these values directly; it must not restate them as literals.
export interface BootstrapCI {
  point: number;
  ci_lower: number;
  ci_upper: number;
  std_error: number;
  n_bootstraps: number;
}

export interface DirectGroundTruthBenchmark {
  events_evaluated: number;
  events_in_population: number;
  events_missing_ground_truth: number;
  direct_true_o1_policy_ev_inr: number;
  direct_true_oracle_best_ev_inr: number;
  direct_true_baseline_policy_ev_inr: number;
  direct_true_regret_inr_per_event: number;
  direct_policy_efficiency: number;
  direct_uplift_over_baseline_inr_per_event: number;
  direct_uplift_over_baseline_pct: number;
  per_event_dominance_violations: number;
  action_matches_oracle_best_rate: number;
}

export interface SnipsEvaluation {
  logged_policy_realized_mean_ev_inr: number;
  baseline_policy_snips_ev_inr: number;
  baseline_policy_snips_ci: BootstrapCI;
  baseline_policy_coverage_rate: number;
  baseline_effective_sample_size: number;
  ml_policy_snips_ev_inr: number;
  ml_policy_snips_ci: BootstrapCI;
  ml_policy_coverage_rate: number;
  ml_matched_events: number;
  ml_effective_sample_size: number;
  ml_effective_sample_size_fraction: number;
  min_logging_propensity: number;
  max_importance_weight: number;
  snips_uplift_over_baseline_inr_per_event: number;
  snips_minus_direct_true_ev_inr: number;
}

export interface ScenarioResult {
  parameters?: Record<string, number>;
  ml_policy_ev_ci: { mean: number; ci_lower: number; ci_upper: number };
  baseline_policy_ev_ci: { mean: number; ci_lower: number; ci_upper: number };
  oracle_best_ev_ci: { mean: number; ci_lower: number; ci_upper: number };
  uplift_ci: { mean: number };
  regret_ci: { mean: number };
  ranking_stable?: boolean;
  safety_violations?: number;
}

export interface EvaluationSummary {
  task11_model_results?: {
    selected_model?: string;
    train_metrics?: ModelMetrics;
    validation_metrics?: ModelMetrics;
    test_metrics?: ModelMetrics;
  };
  task11_policy_evaluation?: {
    test_events_count?: number;
    safety_evaluation?: {
      safety_violations_count: number;
      safety_violation_rate: number;
    };
    direct_ground_truth_benchmark?: DirectGroundTruthBenchmark;
    off_policy_snips_evaluation?: SnipsEvaluation;
    distributions?: {
      ml_action_distribution?: Record<string, number>;
      confidence_distribution?: Record<string, number>;
    };
  };
  task12_robustness?: {
    economic_sensitivity?: Record<string, ScenarioResult>;
    ground_truth_robustness?: Record<string, ScenarioResult>;
    distribution_shifts?: Record<string, ScenarioResult>;
    ablation_study?: Record<string, {
      mean_oracle_ev_inr: number;
      events_evaluated: number;
      events_in_population: number;
      events_missing_ground_truth: number;
      safety_violations_count: number;
      safety_violation_rate: number;
    }>;
  };
}

export interface ModelMetrics {
  roc_auc: number;
  brier_score: number;
  log_loss: number;
  mean_calibration_error: number;
}
