interface QuestionCardProps {
  questionNumber: number;
  questionText: string;
  maxQuestions: number;
}

export default function QuestionCard({
  questionNumber,
  questionText,
  maxQuestions,
}: QuestionCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 p-6 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/50 px-2 py-1 rounded-full">
          Question {questionNumber} of {maxQuestions}
        </span>
      </div>
      <p className="text-gray-800 dark:text-gray-200 text-lg leading-relaxed">
        {questionText}
      </p>
    </div>
  );
}
