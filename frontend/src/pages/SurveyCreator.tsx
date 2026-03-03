import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import SurveyForm from '../components/SurveyForm';
import * as api from '../services/api';
import type { CreateSurveyRequest } from '../types/survey';

export default function SurveyCreator() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: CreateSurveyRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const survey = await api.createSurvey(data);
      navigate(`/admin/surveys/${survey.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create survey');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          to="/admin"
          className="text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium transition-colors"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-gray-900 dark:text-white">Create New Survey</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure your conversational survey. The AI will generate dynamic questions based on your settings.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <div className="flex items-center">
            <span className="text-red-400 mr-2">⚠️</span>
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 shadow-sm dark:shadow-gray-900/20 rounded-lg border border-gray-200 dark:border-gray-700 p-6 transition-colors">
        <SurveyForm
          onSubmit={handleSubmit}
          submitLabel="Create Survey"
          isLoading={isLoading}
        />
      </div>

      {/* Cancel */}
      <div className="mt-4 text-center">
        <Link
          to="/admin"
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors"
        >
          Cancel
        </Link>
      </div>
    </div>
  );
}
