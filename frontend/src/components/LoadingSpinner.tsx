interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  message?: string;
}

export default function LoadingSpinner({
  size = "md",
  message,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <div className="flex flex-col items-center justify-center py-8">
      <div
        className={`${sizeClasses[size]} animate-spin rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-indigo-600 dark:border-t-indigo-400`}
      />
      {message && (
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">{message}</p>
      )}
    </div>
  );
}
