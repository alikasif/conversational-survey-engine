interface ProgressBarProps {
  current: number;
  total: number;
  label?: string;
}

export default function ProgressBar({
  current,
  total,
  label,
}: ProgressBarProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">{label}</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {current}/{total}
          </span>
        </div>
      )}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className="bg-indigo-600 dark:bg-indigo-500 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
