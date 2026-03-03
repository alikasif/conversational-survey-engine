/** Session-related TypeScript interfaces matching the API contract. */

export interface CreateSessionRequest {
  participant_name?: string;
  metadata?: Record<string, string>;
}

export interface QuestionPayload {
  question_id: string;
  text: string;
  question_number: number;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  survey_id: string;
  status: "active" | "completed" | "exited";
  current_question: QuestionPayload;
  question_number: number;
  max_questions: number;
  created_at: string;
}

export interface SubmitAnswerRequest {
  answer: string;
  question_id?: string;
  question_text?: string;
}

export interface NextQuestionResponse {
  session_id: string;
  status: "active" | "completed";
  question?: QuestionPayload;
  completion_reason?: string;
  question_number: number;
  max_questions: number;
}

export interface ConversationEntry {
  question_id: string;
  question_text: string;
  answer_text: string;
  question_number: number;
  answered_at: string;
}

export interface SessionDetailResponse {
  session_id: string;
  user_id: string;
  survey_id: string;
  status: "active" | "completed" | "exited";
  conversation: ConversationEntry[];
  question_count: number;
  created_at: string;
  completed_at?: string;
}

export interface SessionCompleteResponse {
  session_id: string;
  status: "exited";
  question_count: number;
  message: string;
}

export interface ResponseListResponse {
  responses: SessionDetailResponse[];
  total: number;
  skip: number;
  limit: number;
}
