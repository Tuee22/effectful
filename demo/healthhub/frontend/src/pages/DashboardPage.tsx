/**
 * DashboardPage - Main dashboard for authenticated users.
 */

import { useAuth } from '../hooks/useAuth'
import './DashboardPage.css'

export const DashboardPage = () => {
  const { authState, role } = useAuth()

  const email = authState.type === 'Authenticated' ? authState.email : null

  return (
    <div className="dashboard-page">
      <h1>Welcome to HealthHub</h1>

      {email && (
        <p className="welcome-message">
          Signed in as <strong>{email}</strong>
        </p>
      )}

      <div className="dashboard-cards">
        {role === 'patient' && (
          <>
            <div className="dashboard-card">
              <h3>My Appointments</h3>
              <p>View and manage your scheduled appointments.</p>
              <a href="/appointments">View Appointments</a>
            </div>
            <div className="dashboard-card">
              <h3>My Prescriptions</h3>
              <p>View your active prescriptions and medication history.</p>
              <a href="/prescriptions">View Prescriptions</a>
            </div>
          </>
        )}

        {role === 'doctor' && (
          <>
            <div className="dashboard-card">
              <h3>Today's Schedule</h3>
              <p>View appointments scheduled for today.</p>
              <a href="/appointments">View Schedule</a>
            </div>
            <div className="dashboard-card">
              <h3>Patient Records</h3>
              <p>Access patient medical records.</p>
              <a href="/patients">View Patients</a>
            </div>
            <div className="dashboard-card">
              <h3>Prescriptions</h3>
              <p>Manage and create prescriptions.</p>
              <a href="/prescriptions">View Prescriptions</a>
            </div>
          </>
        )}

        {role === 'admin' && (
          <>
            <div className="dashboard-card">
              <h3>All Appointments</h3>
              <p>Manage all appointments in the system.</p>
              <a href="/appointments">View Appointments</a>
            </div>
            <div className="dashboard-card">
              <h3>All Patients</h3>
              <p>Access all patient records.</p>
              <a href="/patients">View Patients</a>
            </div>
            <div className="dashboard-card">
              <h3>System Overview</h3>
              <p>View system statistics and reports.</p>
              <a href="#">View Reports</a>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
