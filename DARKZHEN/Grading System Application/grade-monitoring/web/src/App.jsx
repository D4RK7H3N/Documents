import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { setSessionExpiredHandler } from "./api/client";
import Layout from "./components/Layout";
import { Btn, Spinner } from "./components/ui";
import { useAuth } from "./auth/AuthContext";
import ChangePassword from "./pages/ChangePassword";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Dashboard from "./pages/Dashboard";
import MyClasses from "./pages/MyClasses";
import Gradebook from "./pages/Gradebook";
import ClassReport from "./pages/ClassReport";
import Students from "./pages/Students";
import StudentRecord from "./pages/StudentRecord";
import Teachers from "./pages/Teachers";
import Users from "./pages/Users";
import Academics from "./pages/Academics";
import GradingConfig from "./pages/GradingConfig";
import AuditLog from "./pages/AuditLog";
import Submissions from "./pages/Submissions";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

function Guard({ role, children }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  if (user.role === "student") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-space-lg">
        <div className="max-w-md bg-surface-container-lowest rounded-xl shadow-sm p-space-2xl text-center">
          <img src="/logo.svg" alt="" className="w-12 h-12 mx-auto mb-space-md" />
          <h1 className="font-headline-md text-headline-md text-on-surface">Students use the mobile app</h1>
          <p className="mt-space-sm font-body-md text-body-md text-on-surface-variant">
            This web portal is for teachers and administrators. Open the mobile app to view your grades.
          </p>
          <Btn className="mt-space-lg justify-center" icon="logout" onClick={() => logout()}>
            Log out
          </Btn>
        </div>
      </div>
    );
  }
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
}

const adminOnly = (page) => <Guard role="admin">{page}</Guard>;
const teacherOnly = (page) => <Guard role="teacher">{page}</Guard>;

export default function App() {
  const navigate = useNavigate();

  useEffect(() => {
    setSessionExpiredHandler(() => navigate("/login", { replace: true }));
  }, [navigate]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ChangePassword />} />
      <Route path="/" element={<Guard><Dashboard /></Guard>} />
      <Route path="/classes" element={<Guard><MyClasses /></Guard>} />
      <Route path="/gradebook/:classId" element={<Guard><Gradebook /></Guard>} />
      <Route path="/classes/:classId/report" element={<Guard><ClassReport /></Guard>} />
      <Route
        path="/submissions"
        element={
          <Guard>
            <Submissions />
          </Guard>
        }
      />
      <Route
        path="/reports"
        element={
          <Guard>
            <Reports />
          </Guard>
        }
      />
      <Route path="/profile" element={<Guard><Profile /></Guard>} />
      <Route path="/students" element={adminOnly(<Students />)} />
      <Route path="/students/:studentId/record" element={adminOnly(<StudentRecord />)} />
      <Route path="/teachers" element={adminOnly(<Teachers />)} />
      <Route path="/users" element={adminOnly(<Users />)} />
      <Route path="/academics" element={adminOnly(<Academics />)} />
      <Route path="/grading-config" element={adminOnly(<GradingConfig />)} />
      <Route path="/settings" element={adminOnly(<Settings />)} />
      <Route path="/audit-log" element={adminOnly(<AuditLog />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
