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
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-gray-900">Create New Survey</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure your conversational survey. The AI will generate dynamic questions based on your settings.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center">
            <span className="text-red-400 mr-2">⚠️</span>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="bg-white shadow-sm rounded-lg border border-gray-200 p-6">
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
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </Link>
      </div>
    </div>
  );
}
