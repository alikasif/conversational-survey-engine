import { useState, useEffect, useCallback } from 'react';
import { SurveyResponse, CreateSurveyRequest } from '../types/survey';
import * as api from '../services/api';

export function useAdminSurveys() {
  const [surveys, setSurveys] = useState<SurveyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSurveys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listSurveys();
      setSurveys(response.surveys);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch surveys');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSurveys(); }, [fetchSurveys]);

  const createSurvey = async (data: CreateSurveyRequest): Promise<SurveyResponse> => {
    const survey = await api.createSurvey(data);
    await fetchSurveys();
    return survey;
  };

  const deleteSurvey = async (id: string): Promise<void> => {
    await api.deleteSurvey(id);
    await fetchSurveys();
  };

  return { surveys, loading, error, fetchSurveys, createSurvey, deleteSurvey };
}
