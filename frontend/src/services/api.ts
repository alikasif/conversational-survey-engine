/** Fetch-based API client for the Conversational Survey Engine. */

import type {
  CreateSurveyRequest,
  PresetQuestion,
  SurveyDetailResponse,
  SurveyListResponse,
  SurveyResponse,
  SurveyStatsResponse,
  UpdateSurveyRequest,
} from "../types/survey";
import type {
  CreateSessionRequest,
  NextQuestionResponse,
  ResponseListResponse,
  SessionCompleteResponse,
  SessionDetailResponse,
  SessionResponse,
  SubmitAnswerRequest,
} from "../types/session";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(
      `API error ${res.status}: ${errorBody || res.statusText}`
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

// ── Admin: Surveys ──────────────────────────────────────────────

export async function createSurvey(
  data: CreateSurveyRequest
): Promise<SurveyResponse> {
  return request<SurveyResponse>("/admin/surveys", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listSurveys(
  skip = 0,
  limit = 20
): Promise<SurveyListResponse> {
  return request<SurveyListResponse>(
    `/admin/surveys?skip=${skip}&limit=${limit}`
  );
}

export async function getSurvey(
  surveyId: string
): Promise<SurveyDetailResponse> {
  return request<SurveyDetailResponse>(`/admin/surveys/${surveyId}`);
}

export async function updateSurvey(
  surveyId: string,
  data: UpdateSurveyRequest
): Promise<SurveyResponse> {
  return request<SurveyResponse>(`/admin/surveys/${surveyId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSurvey(surveyId: string): Promise<void> {
  return request<void>(`/admin/surveys/${surveyId}`, {
    method: "DELETE",
  });
}

export async function getSurveyResponses(
  surveyId: string,
  skip = 0,
  limit = 20
): Promise<ResponseListResponse> {
  return request<ResponseListResponse>(
    `/admin/surveys/${surveyId}/responses?skip=${skip}&limit=${limit}`
  );
}

export async function getSurveyStats(
  surveyId: string
): Promise<SurveyStatsResponse> {
  return request<SurveyStatsResponse>(
    `/admin/surveys/${surveyId}/stats`
  );
}

export async function generatePresetQuestions(
  surveyId: string
): Promise<{ questions: PresetQuestion[]; generated_at: string }> {
  return request<{ questions: PresetQuestion[]; generated_at: string }>(
    `/admin/surveys/${surveyId}/generate-questions`,
    { method: "POST" }
  );
}

export async function updatePresetQuestions(
  surveyId: string,
  questions: PresetQuestion[]
): Promise<void> {
  return request<void>(
    `/admin/surveys/${surveyId}/preset-questions`,
    {
      method: "PUT",
      body: JSON.stringify({ questions }),
    }
  );
}

// ── Participant: Sessions ───────────────────────────────────────

export async function createSession(
  surveyId: string,
  data?: CreateSessionRequest
): Promise<SessionResponse> {
  return request<SessionResponse>(`/surveys/${surveyId}/sessions`, {
    method: "POST",
    body: JSON.stringify(data || {}),
  });
}

export async function submitAnswer(
  surveyId: string,
  sessionId: string,
  data: SubmitAnswerRequest
): Promise<NextQuestionResponse> {
  return request<NextQuestionResponse>(
    `/surveys/${surveyId}/sessions/${sessionId}/respond`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function getSession(
  surveyId: string,
  sessionId: string
): Promise<SessionDetailResponse> {
  return request<SessionDetailResponse>(
    `/surveys/${surveyId}/sessions/${sessionId}`
  );
}

export async function exitSession(
  surveyId: string,
  sessionId: string
): Promise<SessionCompleteResponse> {
  return request<SessionCompleteResponse>(
    `/surveys/${surveyId}/sessions/${sessionId}/exit`,
    { method: "POST" }
  );
}
