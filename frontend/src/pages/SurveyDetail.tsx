import { useState, useEffect } from 'react';
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
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Failed to load survey</h2>
        <p className="text-gray-500 mb-4">{error || 'Survey not found'}</p>
        <Link to="/admin" className="text-indigo-600 hover:text-indigo-800 font-medium text-sm">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link to="/admin" className="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
          ← Back to Dashboard
        </Link>
        <div className="mt-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{survey.title}</h1>
            <span
              className={`mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                survey.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
              }`}
            >
              {survey.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <button
            onClick={handleDelete}
            className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100"
          >
            Delete Survey
          </button>
        </div>
      </div>

      {/* Share Link */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-indigo-900 mb-2">Participant Link</h3>
        <div className="flex items-center gap-3">
          <input
            readOnly
            value={participantLink}
            className="flex-1 bg-white border border-indigo-200 rounded-md px-3 py-2 text-sm text-gray-700 select-all"
          />
          <button
            onClick={copyLink}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 whitespace-nowrap"
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

      {/* Survey Config */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Survey Configuration</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Goal</dt>
            <dd className="mt-1 text-sm text-gray-900">{survey.goal}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Context</dt>
            <dd className="mt-1 text-sm text-gray-900">{survey.context}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Max Questions</dt>
            <dd className="mt-1 text-sm text-gray-900">{survey.max_questions}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Completion Criteria</dt>
            <dd className="mt-1 text-sm text-gray-900">{survey.completion_criteria || '—'}</dd>
          </div>
          {survey.constraints.length > 0 && (
            <div className="md:col-span-2">
              <dt className="text-sm font-medium text-gray-500">Constraints</dt>
              <dd className="mt-1">
                <ul className="list-disc list-inside text-sm text-gray-900 space-y-1">
                  {survey.constraints.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
          <div>
            <dt className="text-sm font-medium text-gray-500">Goal Coverage Threshold</dt>
            <dd className="mt-1 text-sm text-gray-900">{(survey.goal_coverage_threshold * 100).toFixed(0)}%</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Context Similarity Threshold</dt>
            <dd className="mt-1 text-sm text-gray-900">{(survey.context_similarity_threshold * 100).toFixed(0)}%</dd>
          </div>
        </dl>
      </div>

      {/* Top Themes */}
      {stats?.top_themes && stats.top_themes.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Themes</h2>
          <div className="flex flex-wrap gap-2">
            {stats.top_themes.map((theme, i) => (
              <span key={i} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-50 text-indigo-700">
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sessions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Sessions</h2>
        </div>
        {sessions.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-gray-500">No sessions yet. Share the participant link to start collecting responses.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Session ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Questions</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completed</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sessions.map(session => (
                  <tr key={session.session_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                      {session.session_id.slice(0, 8)}…
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          session.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : session.status === 'active'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {session.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {session.question_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(session.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
