import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Trials from "./pages/Trials";
import TrialNew from "./pages/TrialNew";
import TrialDetail from "./pages/TrialDetail";
import Patients from "./pages/Patients";
import PatientDetail from "./pages/PatientDetail";
import PatientForm from "./pages/PatientForm";

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="center-screen">Loading…</div>;
  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/trials" element={<Trials />} />
        <Route path="/trials/new" element={<TrialNew />} />
        <Route path="/trials/:id" element={<TrialDetail />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/patients/new" element={<PatientForm />} />
        <Route path="/patients/:id" element={<PatientDetail />} />
        <Route path="/patients/:id/edit" element={<PatientForm />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
