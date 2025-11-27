/**
 * App - Main application component with routing.
 * Uses React Router for navigation and ProtectedRoute for auth guards.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { ProtectedRoute } from './components/common/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { AppointmentsPage } from './pages/AppointmentsPage'
import { AppointmentDetailPage } from './pages/AppointmentDetailPage'
import { PatientsPage } from './pages/PatientsPage'
import { PrescriptionsPage } from './pages/PrescriptionsPage'
import { LabResultsPage } from './pages/LabResultsPage'
import { InvoicesPage } from './pages/InvoicesPage'

export const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes with layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          {/* Dashboard - accessible to all authenticated users */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />

          {/* Appointments - accessible to all authenticated users */}
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="appointments/:id" element={<AppointmentDetailPage />} />

          {/* Patients - doctors and admins only */}
          <Route
            path="patients"
            element={
              <ProtectedRoute requiredRoles={['doctor', 'admin']}>
                <PatientsPage />
              </ProtectedRoute>
            }
          />

          {/* Prescriptions - accessible to all authenticated users */}
          <Route path="prescriptions" element={<PrescriptionsPage />} />

          {/* Lab Results - accessible to all authenticated users */}
          <Route path="lab-results" element={<LabResultsPage />} />

          {/* Invoices - accessible to all authenticated users */}
          <Route path="invoices" element={<InvoicesPage />} />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
