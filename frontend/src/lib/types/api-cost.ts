export interface CostSeriesPoint {
  date: string;
  cost_usd: number;
  total_tokens: number;
  mail_count: number;
}

export interface CostsResponse {
  series: CostSeriesPoint[];
  total_usd: number;
}
