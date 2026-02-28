import { Link, Outlet, useLocation } from "react-router-dom";

export default function Layout() {
  const location = useLocation();

  const isAdmin = location.pathname.startsWith("/admin");

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link
                to="/"
                className="text-xl font-bold text-indigo-600 hover:text-indigo-700"
              >
                CSE
              </Link>
              <span className="ml-2 text-sm text-gray-500">
                Conversational Survey Engine
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/admin"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isAdmin
                    ? "bg-indigo-100 text-indigo-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Admin
              </Link>
              <Link
                to="/survey"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  !isAdmin && location.pathname.startsWith("/survey")
                    ? "bg-indigo-100 text-indigo-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Take Survey
              </Link>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
