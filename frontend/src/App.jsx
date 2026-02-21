import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import InterviewLayout from "./components/InterviewLayout";
import DashboardLayout from "./components/layout/DashboardLayout";

// Auth pages
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";
import ForgotPasswordPage from "./pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";

// Dashboard pages
import DashboardPage from "./pages/dashboard/DashboardPage";
import CampaignCreatePage from "./pages/dashboard/CampaignCreatePage";
import CampaignDetailPage from "./pages/dashboard/CampaignDetailPage";
import CandidateDetailPage from "./pages/dashboard/CandidateDetailPage";
import SettingsPage from "./pages/dashboard/SettingsPage";
import ReviewQueuePage from "./pages/dashboard/ReviewQueuePage";
import ReviewSessionPage from "./pages/dashboard/ReviewSessionPage";
import TemplatesPage from "./pages/dashboard/TemplatesPage";
import InsightsPage from "./pages/dashboard/InsightsPage";

// Candidate interview pages
import WelcomePage from "./pages/candidate/WelcomePage";
import ConsentPage from "./pages/candidate/ConsentPage";
import CameraTestPage from "./pages/candidate/CameraTestPage";
import RecordingPage from "./pages/candidate/RecordingPage";
import ReviewPage from "./pages/candidate/ReviewPage";
import ConfirmationPage from "./pages/candidate/ConfirmationPage";
import ExpiredPage from "./pages/candidate/ExpiredPage";
import AlreadySubmittedPage from "./pages/candidate/AlreadySubmittedPage";

export default function App() {
  return (
    <Routes>
      {/* Auth routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* HR Dashboard routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="campaigns/new" element={<CampaignCreatePage />} />
        <Route path="campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="candidates/:id" element={<CandidateDetailPage />} />
        <Route path="reviews" element={<ReviewQueuePage />} />
        <Route path="reviews/:candidateId" element={<ReviewSessionPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Candidate interview routes */}
      <Route path="/interview/:token" element={<InterviewLayout />}>
        <Route path="welcome" element={<WelcomePage />} />
        <Route path="consent" element={<ConsentPage />} />
        <Route path="camera" element={<CameraTestPage />} />
        <Route path="record/:qi" element={<RecordingPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="submit" element={<ConfirmationPage />} />
        <Route path="expired" element={<ExpiredPage />} />
        <Route path="submitted" element={<AlreadySubmittedPage />} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
