import { Link, useLocation, useParams } from 'react-router-dom';

interface CompletionState {
  questionCount?: number;
  completionReason?: string;
}

export default function SurveyComplete() {
  const { surveyId } = useParams<{ surveyId: string }>();
  const location = useLocation();
  const state = (location.state as CompletionState) || {};

  const { questionCount, completionReason } = state;

  const isExited = completionReason === 'user_exited';

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="max-w-md w-full text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-6">
          <span className="text-4xl">{isExited ? '👋' : '🎉'}</span>
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-3">
          {isExited ? 'Survey Exited' : 'Thank You!'}
        </h1>

        <p className="text-gray-500 leading-relaxed mb-8">
          {isExited
            ? 'You have exited the survey. Your responses up to this point have been saved.'
            : 'Your responses have been recorded successfully. Thank you for taking the time to share your thoughts!'}
        </p>

        {/* Summary */}
        {(questionCount !== undefined) && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Summary</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-bold text-indigo-600">{questionCount}</p>
                <p className="text-sm text-gray-500">Questions Answered</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-indigo-600 capitalize">
                  {isExited ? 'Exited' : 'Completed'}
                </p>
                <p className="text-sm text-gray-500">Status</p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {surveyId && (
            <Link
              to={`/survey?id=${surveyId}`}
              className="block w-full py-2.5 px-4 border border-indigo-600 text-indigo-600 rounded-md text-sm font-medium hover:bg-indigo-50 transition-colors"
            >
              Take Survey Again
            </Link>
          )}
          <Link
            to="/"
            className="block w-full py-2.5 px-4 text-gray-500 text-sm hover:text-gray-700 transition-colors"
          >
            Return Home
          </Link>
        </div>
      </div>
    </div>
  );
}
