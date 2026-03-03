import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSurveySession } from '../hooks/useSurveySession';
import ChatBubble from '../components/ChatBubble';
import ProgressBar from '../components/ProgressBar';
import LoadingSpinner from '../components/LoadingSpinner';

export default function ParticipantSurvey() {
  const { surveyId, sessionId } = useParams<{ surveyId: string; sessionId: string }>();
  const navigate = useNavigate();
  const {
    status,
    currentQuestion,
    questionNumber,
    maxQuestions,
    conversation,
    loading,
    error,
    startSession,
    submitAnswer,
    exitSession,
  } = useSurveySession(surveyId || '');

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Start session on mount if idle
  useEffect(() => {
    if (status === 'idle' && surveyId) {
      startSession();
    }
  }, [status, surveyId, startSession]);

  // Redirect on completion/exit (with delay so thank-you message is visible)
  useEffect(() => {
    if (status === 'completed' || status === 'exited') {
      const delay = status === 'completed' ? 3500 : 0;
      const timer = setTimeout(() => {
        navigate(`/survey/${surveyId}/complete`, {
          state: {
            questionCount: conversation.length,
            completionReason: status === 'exited' ? 'user_exited' : 'completed',
          },
        });
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [status, surveyId, navigate, conversation.length]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation, currentQuestion, loading]);

  // Focus input after loading
  useEffect(() => {
    if (!loading && status === 'active') {
      inputRef.current?.focus();
    }
  }, [loading, status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput('');
    await submitAnswer(trimmed);
  };

  const handleExit = async () => {
    if (window.confirm('Are you sure you want to exit? Your progress will be saved.')) {
      await exitSession();
    }
  };

  if (!surveyId || !sessionId) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Invalid survey session.</p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
            <span className="text-2xl">⚠️</span>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Something went wrong</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={() => startSession()}
            className="px-4 py-2 bg-indigo-600 dark:bg-indigo-500 text-white rounded-md hover:bg-indigo-700 dark:hover:bg-indigo-600 text-sm font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (status === 'idle') {
    return <LoadingSpinner size="lg" message="Starting your survey session..." />;
  }

  return (
    <div className="max-w-2xl mx-auto flex flex-col" style={{ height: 'calc(100vh - 10rem)' }}>
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex-1 mr-4">
          <ProgressBar current={questionNumber} total={maxQuestions} label="Progress" />
        </div>
        <button
          onClick={handleExit}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 whitespace-nowrap transition-colors"
        >
          Exit Survey
        </button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto py-6 space-y-2">
        {/* Past conversation */}
        {conversation.map((entry, i) => (
          <div key={i}>
            <ChatBubble message={entry.question} isUser={false} />
            <ChatBubble message={entry.answer} isUser={true} />
          </div>
        ))}

        {/* Current question */}
        {currentQuestion && !loading && status === 'active' && (
          <ChatBubble message={currentQuestion.text} isUser={false} />
        )}

        {/* Thank you message when survey completes */}
        {status === 'completed' && (
          <div className="flex flex-col items-center text-center py-6 space-y-3 animate-fade-in">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-100 dark:bg-green-900/30">
              <span className="text-3xl">🎉</span>
            </div>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">Thank you!</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
              Your responses have been recorded. We really appreciate you taking the time to share your thoughts!
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Redirecting shortly…</p>
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm dark:shadow-gray-900/20 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex space-x-1.5">
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mx-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {status === 'active' && (
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4 pb-2">
        <form onSubmit={handleSubmit} className="flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your answer..."
            disabled={loading || status !== 'active'}
            className="flex-1 rounded-full border border-gray-300 dark:border-gray-600 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:disabled:bg-gray-800 dark:disabled:text-gray-500 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim() || status !== 'active'}
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-indigo-600 dark:bg-indigo-500 text-white hover:bg-indigo-700 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
            </svg>
          </button>
        </form>
      </div>
      )}
    </div>
  );
}
