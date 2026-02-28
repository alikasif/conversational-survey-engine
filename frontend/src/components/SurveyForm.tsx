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
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Title *
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          placeholder="e.g., Customer Satisfaction Survey"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Context *
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          required
          rows={4}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          placeholder="Describe the background and purpose of this survey..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Goal *
        </label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          required
          rows={3}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          placeholder="What do you want to learn from this survey?"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Constraints (one per line)
        </label>
        <textarea
          value={constraintsText}
          onChange={(e) => setConstraintsText(e.target.value)}
          rows={3}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          placeholder="Do not ask about pricing\nKeep questions conversational"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Completion Criteria
        </label>
        <textarea
          value={completionCriteria}
          onChange={(e) => setCompletionCriteria(e.target.value)}
          rows={2}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          placeholder="Describe when the survey should be considered complete..."
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Max Questions
          </label>
          <input
            type="number"
            value={maxQuestions}
            onChange={(e) => setMaxQuestions(Number(e.target.value))}
            min={1}
            max={50}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Goal Coverage Threshold
          </label>
          <input
            type="number"
            value={goalCoverage}
            onChange={(e) => setGoalCoverage(Number(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Context Similarity Threshold
          </label>
          <input
            type="number"
            value={contextSimilarity}
            onChange={(e) => setContextSimilarity(Number(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
