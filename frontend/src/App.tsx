import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireRole } from '@/auth/guards'
import { homeFor, useAuth } from '@/auth/store'
import { DoctorShell } from '@/components/layout/DoctorShell'
import { PatientShell } from '@/components/layout/PatientShell'
import Login from '@/pages/Login'
import PatientsPage from '@/pages/doctor/PatientsPage'
import PatientPage from '@/pages/doctor/PatientPage'
import PatientHome from '@/pages/patient/PatientHome'
import MyAnalysesPage from '@/pages/patient/MyAnalysesPage'
import MyAnalysisPage from '@/pages/patient/MyAnalysisPage'

import AnalysisResultPage from '@/pages/doctor/AnalysisResultPage'
import DemoResult from '@/pages/doctor/DemoResultPage'
import UploadAnalysisPage from '@/pages/patient/UploadAnalysisPage'


export default function App() {
  const role = useAuth((s) => s.role)
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<RequireRole role="doctor" />}>
        <Route path="/doctor" element={<DoctorShell />}>
          <Route index element={<Navigate to="patients" replace />} />
          <Route path="patients" element={<PatientsPage />} />
          <Route path="patients/:patientId" element={<PatientPage />} />
          <Route path="patients/:patientId/analyses/:analysisId" element={<AnalysisResultPage />} />
          {import.meta.env.DEV && <Route path="demo-result" element={<DemoResult />} />}
        </Route>
      </Route>

      <Route element={<RequireRole role="patient" />}>
        <Route path="/patient" element={<PatientShell />}>
          <Route index element={<PatientHome />} />
          <Route path="analyses" element={<MyAnalysesPage />} />
          <Route path="analyses/:analysisId" element={<MyAnalysisPage />} />
          <Route path="upload" element={<UploadAnalysisPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to={homeFor(role)} replace />} />
    </Routes>
  )
}