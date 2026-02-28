import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import type { SurveyDetailResponse } from '../types/survey';
import LoadingSpinner from '../components/LoadingSpinner';

export default function ParticipantLanding() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const surveyId = searchParams.get('id');

  const [survey, setSurvey] = useState<SurveyDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');

  useEffect(() => {
    if (!surveyId) return;
    const fetchSurvey = async () => {
      setLoading(true);
      try {
        const data = await api.getSurvey(surveyId);
        setSurvey(data);
      } catch {
        setError('Survey not found or is no longer available.');
      } finally {
        setLoading(false);
      }
    };
    fetchSurvey();
  }, [surveyId]);

  const handleStart = async () => {
    if (!surveyId) return;
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession(surveyId, {
        participant_name: name.trim() || undefined,
      });
      navigate(`/survey/${surveyId}/session/${session.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start survey');
      setStarting(false);
    }
  };

  // No survey ID provided
  if (!surveyId) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-indigo-100 mb-6">
            <span className="text-4xl">💬</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Conversational Survey Engine</h1>
          <p className="text-gray-500">
            You need a survey link to participate. Please ask the survey creator for a valid link.
          </p>
        </div>
      </div>
    );
  }

  if (loading) return <LoadingSpinner size="lg" message="Loading survey..." />;

  if (error && !survey) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-100 mb-6">
            <span className="text-4xl">😕</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Survey Not Found</h1>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!survey) return null;

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="max-w-lg w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-indigo-100 mb-6">
            <span className="text-4xl">💬</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">{survey.title}</h1>
          <p className="text-gray-500 leading-relaxed">{survey.context}</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-5">
          <div className="text-center">
            <p className="text-sm text-gray-500">
              This is a conversational survey with up to <span className="font-semibold text-gray-700">{survey.max_questions}</span> questions.
              Your responses help us improve.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Name (optional)</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Enter your name"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2.5"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={starting}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {starting ? 'Starting...' : 'Start Survey →'}
          </button>
        </div>
      </div>
    </div>
  );
}
