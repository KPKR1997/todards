export type NullableNumber = number | null;

export interface StageSummary {
  id: string;
  label: string;
  field: string;
  count: number;
  total: NullableNumber;
  average: NullableNumber;
  median: NullableNumber;
  p50: NullableNumber;
  p95: NullableNumber;
  p99: NullableNumber;
  coverage_percent: number;
  share_of_pipeline_percent: NullableNumber;
}

export interface Run {
  run_id: string;
  source_row: number;
  timestamp: string | null;
  duration_seconds: NullableNumber;
  scraped: NullableNumber;
  final_articles: NullableNumber;
  llm_calls: NullableNumber;
  llm_failures: NullableNumber;
  total_tokens: NullableNumber;
  category_validation_status: string | null;
  stages: Record<string, NullableNumber>;
  issues: string[];
}

export interface TrendPoint {
  run_id: string;
  timestamp: string | null;
  duration_seconds?: NullableNumber;
  scraped?: NullableNumber;
  final_articles?: NullableNumber;
  prompt_eval_seconds?: NullableNumber;
  generation_seconds?: NullableNumber;
  load_seconds?: NullableNumber;
  server_total_seconds?: NullableNumber;
  total_tokens?: NullableNumber;
  [key: string]: string | number | null | undefined;
}

export interface DashboardData {
  meta: {
    source: {
      path: string;
      row_count: number;
      columns: string[];
      invalid_row_count: number;
      field_coverage_percent: Record<string, number>;
      last_modified: string;
    };
    selected_row_count: number;
    warnings: string[];
  };
  period: { from: string | null; to: string | null };
  overview: {
    run_count: number;
    successful_runs: null;
    failed_runs: null;
    run_status_note: string;
    latest_run: Run | null;
    duration: { count: number; total: NullableNumber; average: NullableNumber; median: NullableNumber; p50: NullableNumber; p95: NullableNumber; p99: NullableNumber };
    total_scraped: NullableNumber;
    total_final_articles: NullableNumber;
    publication_yield_percent: NullableNumber;
    articles_per_minute: NullableNumber;
    slowest_stage: StageSummary | null;
  };
  duration_trend: TrendPoint[];
  stages: { summary: StageSummary[]; trend: TrendPoint[]; note: string };
  content: {
    funnel: { id: string; label: string; value: NullableNumber; coverage_percent: number }[];
    category_totals: { category: string; articles: NullableNumber; coverage_percent: number }[];
    deduplication: Record<string, NullableNumber>;
    note: string;
  };
  llm: {
    total_calls: NullableNumber;
    total_failures: NullableNumber;
    failure_rate_percent: NullableNumber;
    weighted_average_response_time_seconds: NullableNumber;
    total_prompt_tokens: NullableNumber;
    total_response_tokens: NullableNumber;
    total_tokens: NullableNumber;
    tokens_per_usage_response: NullableNumber;
    tokens_per_final_article: NullableNumber;
    latency_percentiles: null;
    latency_percentiles_note: string;
    token_total_inconsistencies: { run_id: string; timestamp: string | null; expected: number; recorded: number }[];
    trend: TrendPoint[];
  };
  safety: {
    coverage_percent: number;
    values: Record<string, NullableNumber>;
    dry_run_rows: number;
  };
  runs: Run[];
}
