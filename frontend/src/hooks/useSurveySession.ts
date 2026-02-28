import { useState, useCallback } from 'react';
import { SessionResponse, NextQuestionResponse, QuestionPayload } from '../types/session';
import * as api from '../services/api';

interface SurveySessionState {
  sessionId: string | null;
  userId: string | null;
  surveyId: string;
  status: 'idle' | 'active' | 'completed' | 'exited' | 'error';
  currentQuestion: QuestionPayload | null;
  questionNumber: number;
  maxQuestions: number;
  completionReason: string | null;
  conversation: Array<{ question: string; answer: string }>;
  loading: boolean;
  error: string | null;
}

export function useSurveySession(surveyId: string) {
  const [state, setState] = useState<SurveySessionState>({
    sessionId: null,
    userId: null,
    surveyId,
    status: 'idle',
    currentQuestion: null,
    questionNumber: 0,
    maxQuestions: 0,
    completionReason: null,
    conversation: [],
    loading: false,
    error: null,
  });

  const startSession = useCallback(async (participantName?: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response: SessionResponse = await api.createSession(surveyId, { participant_name: participantName });
      setState(prev => ({
        ...prev,
        sessionId: response.session_id,
        userId: response.user_id,
        status: 'active',
        currentQuestion: response.current_question,
        questionNumber: response.question_number,
        maxQuestions: response.max_questions,
        loading: false,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : 'Failed to start session',
        loading: false,
      }));
    }
  }, [surveyId]);

  const submitAnswer = useCallback(async (answer: string) => {
    if (!state.sessionId) return;
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response: NextQuestionResponse = await api.submitAnswer(surveyId, state.sessionId, { answer });
      setState(prev => ({
        ...prev,
        status: response.status === 'completed' ? 'completed' : 'active',
        currentQuestion: response.question || null,
        questionNumber: response.question_number,
        completionReason: response.completion_reason || null,
        conversation: [
          ...prev.conversation,
          { question: prev.currentQuestion?.text || '', answer },
        ],
        loading: false,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to submit answer',
        loading: false,
      }));
    }
  }, [surveyId, state.sessionId, state.currentQuestion]);

  const exitSession = useCallback(async () => {
    if (!state.sessionId) return;
    setState(prev => ({ ...prev, loading: true }));
    try {
      await api.exitSession(surveyId, state.sessionId);
      setState(prev => ({
        ...prev,
        status: 'exited',
        completionReason: 'user_exited',
        loading: false,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to exit session',
        loading: false,
      }));
    }
  }, [surveyId, state.sessionId]);

  return { ...state, startSession, submitAnswer, exitSession };
}
