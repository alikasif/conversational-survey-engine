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
    indigo: "bg-indigo-50 text-indigo-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700",
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
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
