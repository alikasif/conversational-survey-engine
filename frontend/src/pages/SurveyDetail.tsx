import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import type { SurveyDetailResponse, SurveyStatsResponse } from '../types/survey';
import type { SessionDetailResponse } from '../types/session';
import StatsCard from '../components/StatsCard';
import LoadingSpinner from '../components/LoadingSpinner';

export default function SurveyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [survey, setSurvey] = useState<SurveyDetailResponse | null>(null);
  const [stats, setStats] = useState<SurveyStatsResponse | null>(null);
  const [sessions, setSessions] = useState<SessionDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const refreshSurvey = useCallback(async () => {
    if (!id) return;
    try {
      const surveyData = await api.getSurvey(id);
      setSurvey(surveyData);
    } catch (_) {
      // ignore refresh errors
    }
  }, [id]);

  const handleGenerateQuestions = async () => {
    if (!id || !survey) return;
    if (survey.preset_questions && survey.preset_questions.length > 0) {
      if (!window.confirm('This will regenerate all preset questions and replace the existing set. Continue?')) return;
    }
    setGenerating(true);
    setGenerateError(null);
    try {
      await api.generatePresetQuestions(id);
      await refreshSurvey();
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Failed to generate questions');
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [surveyData, statsData, responsesData] = await Promise.all([
          api.getSurvey(id),
          api.getSurveyStats(id).catch(() => null),
          api.getSurveyResponses(id).catch(() => ({ responses: [], total: 0, skip: 0, limit: 20 })),
        ]);
        setSurvey(surveyData);
        setStats(statsData);
        setSessions(responsesData.responses);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load survey');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  const handleDelete = async () => {
    if (!id || !survey) return;
    if (!window.confirm(`Delete "${survey.title}"? This cannot be undone.`)) return;
    try {
      await api.deleteSurvey(id);
      navigate('/admin');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete survey');
    }
  };

  const participantLink = `${window.location.origin}/survey?id=${id}`;

  const copyLink = () => {
    navigator.clipboard.writeText(participantLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (loading) return <LoadingSpinner size="lg" message="Loading survey details..." />;

  if (error || !survey) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Failed to load survey</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">{error || 'Survey not found'}</p>
        <Link to="/admin" className="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium text-sm transition-colors">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link to="/admin" className="text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium transition-colors">
          ← Back to Dashboard
        </Link>
        <div className="mt-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{survey.title}</h1>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  survey.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}
              >
                {survey.is_active ? 'Active' : 'Inactive'}
              </span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  survey.question_mode === 'preset'
                    ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                }`}
              >
                {survey.question_mode === 'preset' ? 'Preset' : 'Dynamic'}
              </span>
            </div>
          </div>
          <button
            onClick={handleDelete}
            className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
          >
            Delete Survey
          </button>
        </div>
      </div>

      {/* Share Link */}
      <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4 transition-colors">
        <h3 className="text-sm font-medium text-indigo-900 dark:text-indigo-300 mb-2">Participant Link</h3>
        <div className="flex items-center gap-3">
          <input
            readOnly
            value={participantLink}
            className="flex-1 bg-white dark:bg-gray-700 border border-indigo-200 dark:border-gray-600 rounded-md px-3 py-2 text-sm text-gray-700 dark:text-gray-200 select-all transition-colors"
          />
          <button
            onClick={copyLink}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 dark:bg-indigo-500 rounded-md hover:bg-indigo-700 dark:hover:bg-indigo-600 whitespace-nowrap transition-colors"
          >
            {copiedLink ? 'Copied!' : 'Copy Link'}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Total Sessions" value={stats?.total_sessions ?? survey.total_sessions ?? 0} icon="👥" color="indigo" />
        <StatsCard label="Completed" value={stats?.completed_sessions ?? survey.completed_sessions ?? 0} icon="✅" color="green" />
        <StatsCard label="Abandoned" value={stats?.abandoned_sessions ?? 0} icon="🚪" color="yellow" />
        <StatsCard
          label="Avg Questions"
          value={stats?.avg_questions_per_session?.toFixed(1) ?? survey.avg_questions_per_session?.toFixed(1) ?? '0'}
          icon="❓"
          color="blue"
        />
      </div>

      {/* Preset Questions (only for preset mode) */}
      {survey.question_mode === 'preset' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 p-6 transition-colors">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Preset Questions</h2>
              {survey.preset_generated_at && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Generated at: {new Date(survey.preset_generated_at).toLocaleString()}
                </p>
              )}
            </div>
            <button
              onClick={handleGenerateQuestions}
              disabled={generating}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-purple-600 dark:bg-purple-500 rounded-md hover:bg-purple-700 dark:hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating…
                </>
              ) : survey.preset_questions && survey.preset_questions.length > 0 ? (
                'Regenerate Questions'
              ) : (
                'Generate Questions'
              )}
            </button>
          </div>

          {generateError && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-700 dark:text-red-400">{generateError}</p>
            </div>
          )}

          {generating && (
            <div className="mb-4 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-md">
              <p className="text-sm text-purple-700 dark:text-purple-400">
                Generating questions using AI — this may take 30–60 seconds…
              </p>
            </div>
          )}

          {!survey.preset_questions || survey.preset_questions.length === 0 ? (
            !generating && (
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                <p className="text-sm text-yellow-800 dark:text-yellow-300">
                  Questions not generated yet. Click "Generate Questions" to create the question set.
                </p>
              </div>
            )
          ) : (
            <ol className="space-y-3">
              {survey.preset_questions.map((q) => (
                <li
                  key={q.question_id}
                  className="flex gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <span className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 text-xs font-bold">
                    {q.question_number}
                  </span>
                  <span className="text-sm text-gray-900 dark:text-gray-200 pt-1">{q.text}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* Survey Config */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 p-6 transition-colors">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Survey Configuration</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Goal</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{survey.goal}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Context</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{survey.context}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Max Questions</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{survey.max_questions}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Completion Criteria</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{survey.completion_criteria || '—'}</dd>
          </div>
          {survey.constraints.length > 0 && (
            <div className="md:col-span-2">
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Constraints</dt>
              <dd className="mt-1">
                <ul className="list-disc list-inside text-sm text-gray-900 dark:text-gray-200 space-y-1">
                  {survey.constraints.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Goal Coverage Threshold</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{(survey.goal_coverage_threshold * 100).toFixed(0)}%</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Context Similarity Threshold</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-gray-200">{(survey.context_similarity_threshold * 100).toFixed(0)}%</dd>
          </div>
        </dl>
      </div>

      {/* Top Themes */}
      {stats?.top_themes && stats.top_themes.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 p-6 transition-colors">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Top Themes</h2>
          <div className="flex flex-wrap gap-2">
            {stats.top_themes.map((theme, i) => (
              <span key={i} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sessions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 transition-colors">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Sessions</h2>
        </div>
        {sessions.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">No sessions yet. Share the participant link to start collecting responses.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Session ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Questions</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Started</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Completed</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {sessions.map(session => (
                  <tr key={session.session_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600 dark:text-gray-300">
                      {session.session_id.slice(0, 8)}…
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          session.status === 'completed'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                            : session.status === 'active'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {session.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
                      {session.question_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(session.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {session.completed_at ? new Date(session.completed_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
