import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import Spinner from "./ui/Spinner";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading, initialize } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated && isLoading) {
      initialize();
    }
  }, [isAuthenticated, isLoading, initialize]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
