/** Survey-related TypeScript interfaces matching the API contract. */

export interface PresetQuestion {
  question_number: number;
  question_id: string;
  text: string;
}

export interface CreateSurveyRequest {
  title: string;
  context: string;
  goal: string;
  constraints: string[];
  max_questions: number;
  completion_criteria: string;
  goal_coverage_threshold?: number;
  context_similarity_threshold?: number;
  question_mode?: 'preset' | 'dynamic';
}

export interface UpdateSurveyRequest {
  title?: string;
  context?: string;
  goal?: string;
  constraints?: string[];
  max_questions?: number;
  completion_criteria?: string;
  goal_coverage_threshold?: number;
  context_similarity_threshold?: number;
  question_mode?: 'preset' | 'dynamic';
}

export interface SurveyResponse {
  id: string;
  title: string;
  context: string;
  goal: string;
  constraints: string[];
  max_questions: number;
  completion_criteria: string;
  goal_coverage_threshold: number;
  context_similarity_threshold: number;
  question_mode: 'preset' | 'dynamic';
  preset_questions?: PresetQuestion[];
  preset_generated_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SurveyListResponse {
  surveys: SurveyResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface SurveyDetailResponse extends SurveyResponse {
  total_sessions: number;
  completed_sessions: number;
  avg_questions_per_session: number;
}

export interface SurveyStatsResponse {
  survey_id: string;
  total_sessions: number;
  completed_sessions: number;
  abandoned_sessions: number;
  avg_questions_per_session: number;
  avg_completion_time_seconds: number;
  top_themes: string[];
}
