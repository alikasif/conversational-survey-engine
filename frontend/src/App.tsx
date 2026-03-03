import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AdminDashboard from "./pages/AdminDashboard";
import SurveyCreator from "./pages/SurveyCreator";
import SurveyDetail from "./pages/SurveyDetail";
import ParticipantLanding from "./pages/ParticipantLanding";
import ParticipantSurvey from "./pages/ParticipantSurvey";
import SurveyComplete from "./pages/SurveyComplete";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/admin" replace />} />
          <Route path="admin" element={<AdminDashboard />} />
          <Route path="admin/surveys/new" element={<SurveyCreator />} />
          <Route path="admin/surveys/:id" element={<SurveyDetail />} />
          <Route path="survey" element={<ParticipantLanding />} />
          <Route
            path="survey/:surveyId/session/:sessionId"
            element={<ParticipantSurvey />}
          />
          <Route
            path="survey/:surveyId/complete"
            element={<SurveyComplete />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
