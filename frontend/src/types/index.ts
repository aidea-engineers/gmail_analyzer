/* API レスポンス型定義 */

export interface KPIs {
  total: number;
  avg_price: number;
  today_count: number;
  area_count: number;
}

export interface SkillCount {
  skill_name: string;
  count: number;
}

export interface PriceData {
  unit_price_min: number | null;
  unit_price_max: number | null;
  unit_price: string;
}

export interface AreaCount {
  work_area: string;
  count: number;
}

export interface TrendData {
  period: string;
  count: number;
}

export interface ChartsResponse {
  skills: SkillCount[];
  prices: PriceData[];
  areas: AreaCount[];
  trend: TrendData[];
}

export interface JobListing {
  id: number;
  company_name: string;
  job_type: string;
  work_area: string;
  unit_price: string;
  unit_price_min: number | null;
  unit_price_max: number | null;
  required_skills: string[];
  project_details: string;
  requirements: string;
  confidence: number;
  start_month: string;
  subject: string;
  sender: string;
  received_at: string;
  created_at: string;
}

export interface ListingsResponse {
  total: number;
  listings: JobListing[];
}

export interface SearchFilters {
  skills: string[];
  areas: string[];
  job_types: string[];
}

export interface FetchStatus {
  gmail_connected: boolean;
  gemini_api_key_set: boolean;
  total_emails: number;
  processed_emails: number;
  unprocessed_emails: number;
  total_listings: number;
}

export interface FetchLog {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  emails_fetched: number;
  emails_processed: number;
  errors: string;
  query_used: string;
}

export interface Settings {
  gemini_model: string;
  gemini_api_key_set: boolean;
  gmail_labels: string[];
  gmail_keywords: string[];
  batch_size: number;
  max_emails_per_fetch: number;
  gemini_delay_seconds: number;
  db_path: string;
}

export interface SettingsUpdate {
  gemini_api_key?: string;
  gemini_model?: string;
  gmail_labels?: string;
  gmail_keywords?: string;
  batch_size?: number;
  max_emails_per_fetch?: number;
  gemini_delay_seconds?: number;
}

export interface JobProgress {
  phase: string;
  current: number;
  total: number;
  message: string;
  done?: boolean;
  result?: {
    emails_fetched: number;
    emails_processed: number;
    listings_created: number;
    api_errors: number;
    status: string;
  };
}
