interface ChatBubbleProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
}

export default function ChatBubble({
  message,
  isUser,
  timestamp,
}: ChatBubbleProps) {
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 transition-colors ${
          isUser
            ? "bg-indigo-600 dark:bg-indigo-500 text-white rounded-br-md"
            : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 shadow-sm dark:shadow-gray-900/20 rounded-bl-md"
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {message}
        </p>
        {timestamp && (
          <p
            className={`text-xs mt-1 ${
              isUser ? "text-indigo-200" : "text-gray-400 dark:text-gray-500"
            }`}
          >
            {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
