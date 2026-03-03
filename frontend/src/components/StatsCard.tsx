interface StatsCardProps {
  label: string;
  value: string | number;
  icon?: string;
  color?: "indigo" | "green" | "yellow" | "red" | "blue";
}

export default function StatsCard({
  label,
  value,
  icon,
  color = "indigo",
}: StatsCardProps) {
  const colorClasses = {
    indigo: "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
    green: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    yellow: "bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
    red: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    blue: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20 border border-gray-200 dark:border-gray-700 p-6 transition-colors">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
        </div>
        {icon && (
          <div
            className={`rounded-full p-3 ${colorClasses[color]}`}
          >
            <span className="text-xl">{icon}</span>
          </div>
        )}
      </div>
    </div>
  );
}
