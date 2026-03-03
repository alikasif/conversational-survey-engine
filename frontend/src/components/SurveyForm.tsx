import { useState } from "react";
import type { CreateSurveyRequest } from "../types/survey";

interface SurveyFormProps {
  initialData?: Partial<CreateSurveyRequest>;
  onSubmit: (data: CreateSurveyRequest) => Promise<void>;
  submitLabel?: string;
  isLoading?: boolean;
}

export default function SurveyForm({
  initialData,
  onSubmit,
  submitLabel = "Create Survey",
  isLoading = false,
}: SurveyFormProps) {
  const [title, setTitle] = useState(initialData?.title || "");
  const [context, setContext] = useState(initialData?.context || "");
  const [goal, setGoal] = useState(initialData?.goal || "");
  const [constraintsText, setConstraintsText] = useState(
    initialData?.constraints?.join("\n") || ""
  );
  const [maxQuestions, setMaxQuestions] = useState(
    initialData?.max_questions || 10
  );
  const [completionCriteria, setCompletionCriteria] = useState(
    initialData?.completion_criteria || ""
  );
  const [goalCoverage, setGoalCoverage] = useState(
    initialData?.goal_coverage_threshold || 0.85
  );
  const [contextSimilarity, setContextSimilarity] = useState(
    initialData?.context_similarity_threshold || 0.7
  );
  const [questionMode, setQuestionMode] = useState<'preset' | 'dynamic'>(
    initialData?.question_mode || 'dynamic'
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const constraints = constraintsText
      .split("\n")
      .map((c) => c.trim())
      .filter(Boolean);

    await onSubmit({
      title,
      context,
      goal,
      constraints,
      max_questions: maxQuestions,
      completion_criteria: completionCriteria,
      goal_coverage_threshold: goalCoverage,
      context_similarity_threshold: contextSimilarity,
      question_mode: questionMode,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Title *
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 transition-colors"
          placeholder="e.g., Customer Satisfaction Survey"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Context *
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          required
          rows={4}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 transition-colors"
          placeholder="Describe the background and purpose of this survey..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Goal *
        </label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          required
          rows={3}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 transition-colors"
          placeholder="What do you want to learn from this survey?"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Constraints (one per line)
        </label>
        <textarea
          value={constraintsText}
          onChange={(e) => setConstraintsText(e.target.value)}
          rows={3}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 transition-colors"
          placeholder="Do not ask about pricing\nKeep questions conversational"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Completion Criteria
        </label>
        <textarea
          value={completionCriteria}
          onChange={(e) => setCompletionCriteria(e.target.value)}
          rows={2}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 transition-colors"
          placeholder="Describe when the survey should be considered complete..."
        />
      </div>

      {/* Question Mode */}
      <fieldset>
        <legend className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Question Mode
        </legend>
        <div className="space-y-3">
          <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
            questionMode === 'dynamic'
              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 dark:border-indigo-400'
              : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
          }`}>
            <input
              type="radio"
              name="question_mode"
              value="dynamic"
              checked={questionMode === 'dynamic'}
              onChange={() => setQuestionMode('dynamic')}
              className="mt-0.5 h-4 w-4 text-indigo-600 focus:ring-indigo-500 dark:focus:ring-offset-gray-800"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">Dynamic</span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                AI generates unique questions per participant based on their responses.
              </p>
            </div>
          </label>
          <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
            questionMode === 'preset'
              ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 dark:border-purple-400'
              : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
          }`}>
            <input
              type="radio"
              name="question_mode"
              value="preset"
              checked={questionMode === 'preset'}
              onChange={() => setQuestionMode('preset')}
              className="mt-0.5 h-4 w-4 text-purple-600 focus:ring-purple-500 dark:focus:ring-offset-gray-800"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">Preset</span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                AI generates a fixed set of questions once — same for all participants.
              </p>
            </div>
          </label>
        </div>
      </fieldset>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Max Questions
          </label>
          <input
            type="number"
            value={maxQuestions}
            onChange={(e) => setMaxQuestions(Number(e.target.value))}
            min={1}
            max={50}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Goal Coverage Threshold
          </label>
          <input
            type="number"
            value={goalCoverage}
            onChange={(e) => setGoalCoverage(Number(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Context Similarity Threshold
          </label>
          <input
            type="number"
            value={contextSimilarity}
            onChange={(e) => setContextSimilarity(Number(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
