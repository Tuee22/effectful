/**
 * AppointmentList component - List of appointments.
 */

import { Link } from 'react-router-dom'
import { Appointment } from '../../models/Appointment'
import { AppointmentStatusBadge } from './AppointmentStatusBadge'
import './AppointmentList.css'

interface AppointmentListProps {
  readonly appointments: readonly Appointment[]
}

export const AppointmentList = ({ appointments }: AppointmentListProps) => {
  if (appointments.length === 0) {
    return (
      <div className="appointment-list-empty">
        <p>No appointments found.</p>
      </div>
    )
  }

  return (
    <div className="appointment-list">
      <table className="appointment-table">
        <thead>
          <tr>
            <th>Reason</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((appointment) => (
            <tr key={appointment.id}>
              <td>{appointment.reason}</td>
              <td>
                <AppointmentStatusBadge status={appointment.status} />
              </td>
              <td>{appointment.createdAt.toLocaleDateString()}</td>
              <td>
                <Link
                  to={`/appointments/${appointment.id}`}
                  className="appointment-view-link"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
