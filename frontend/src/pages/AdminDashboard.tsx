import { Link } from 'react-router-dom';
import { useAdminSurveys } from '../hooks/useAdminSurveys';
import StatsCard from '../components/StatsCard';
import LoadingSpinner from '../components/LoadingSpinner';

export default function AdminDashboard() {
  const { surveys, loading, error, deleteSurvey } = useAdminSurveys();

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"? This action cannot be undone.`)) return;
    try {
      await deleteSurvey(id);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete survey');
    }
  };

  if (loading) return <LoadingSpinner size="lg" message="Loading surveys..." />;

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Failed to load surveys</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-indigo-600 dark:bg-indigo-500 text-white rounded-md hover:bg-indigo-700 dark:hover:bg-indigo-600 text-sm font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const activeSurveys = surveys.filter(s => s.is_active).length;
  const totalSurveys = surveys.length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Manage your conversational surveys</p>
        </div>
        <Link
          to="/admin/surveys/new"
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-900 transition-colors"
        >
          + Create New Survey
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatsCard label="Total Surveys" value={totalSurveys} icon="📋" color="indigo" />
        <StatsCard label="Active Surveys" value={activeSurveys} icon="✅" color="green" />
        <StatsCard label="Inactive Surveys" value={totalSurveys - activeSurveys} icon="⏸️" color="yellow" />
      </div>

      {/* Survey List */}
      {surveys.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 transition-colors">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-900/30 mb-4">
            <span className="text-3xl">📝</span>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No surveys yet</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">Create your first survey to get started.</p>
          <Link
            to="/admin/surveys/new"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 transition-colors"
          >
            + Create Survey
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {surveys.map(survey => (
            <div
              key={survey.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white line-clamp-1">{survey.title}</h3>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        survey.question_mode === 'preset'
                          ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                          : 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                      }`}
                    >
                      {survey.question_mode === 'preset' ? 'Preset' : 'Dynamic'}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        survey.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                      }`}
                    >
                      {survey.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mb-4">{survey.goal}</p>
                <div className="flex items-center text-xs text-gray-400 dark:text-gray-500 space-x-4">
                  <span>Max {survey.max_questions} questions</span>
                  <span>Created {new Date(survey.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="border-t border-gray-100 dark:border-gray-700 px-6 py-3 flex items-center justify-between bg-gray-50 dark:bg-gray-800/50 rounded-b-lg">
                <Link
                  to={`/admin/surveys/${survey.id}`}
                  className="text-sm font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
                >
                  View Details →
                </Link>
                <button
                  onClick={() => handleDelete(survey.id, survey.title)}
                  className="text-sm font-medium text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
