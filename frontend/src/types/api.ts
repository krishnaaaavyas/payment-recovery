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

export interface EvaluationSummary {
  task11_policy_evaluation?: {
    test_events_count?: number;
    safety_violations_count?: number;
    safety_violation_rate?: number;
    evaluation_b_off_policy?: {
      logged_policy_realized_mean_ev?: number;
      baseline_policy_snips_ev?: number;
      ml_policy_snips_ev?: number;
      snips_ev_uplift_over_baseline?: number;
    };
    evaluation_c_oracle_benchmark?: {
      oracle_baseline_policy_ev?: number;
      oracle_ml_policy_ev?: number;
      oracle_best_policy_ev?: number;
      oracle_policy_regret?: number;
    };
    model_predictive_quality?: {
      brier_score?: number;
      log_loss?: number;
      roc_auc?: number;
      mean_calibration_error?: number;
    };
  };
  task12_robustness?: {
    ablation_study?: Record<string, {
      mean_oracle_ev_inr: number;
      safety_violations_count: number;
      safety_violation_rate: number;
    }>;
  };
}
