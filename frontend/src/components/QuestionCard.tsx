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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full">
          Question {questionNumber} of {maxQuestions}
        </span>
      </div>
      <p className="text-gray-800 text-lg leading-relaxed">
        {questionText}
      </p>
    </div>
  );
}
