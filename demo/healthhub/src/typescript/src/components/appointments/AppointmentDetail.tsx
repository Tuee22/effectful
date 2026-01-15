/**
 * AppointmentDetail component - Appointment details view.
 */

import { Appointment, isTerminal } from '../../models/Appointment'
import { AppointmentStatusBadge } from './AppointmentStatusBadge'
import './AppointmentDetail.css'

interface AppointmentDetailProps {
  readonly appointment: Appointment
  readonly onTransition?: (newStatus: string) => void
}

export const AppointmentDetail = ({
  appointment,
  onTransition,
}: AppointmentDetailProps) => {
  const canTransition = onTransition && !isTerminal(appointment.status)

  return (
    <div className="appointment-detail">
      <div className="detail-header">
        <h2>{appointment.reason}</h2>
        <AppointmentStatusBadge status={appointment.status} />
      </div>

      <div className="detail-grid">
        <div className="detail-item">
          <label>Appointment ID</label>
          <span>{appointment.id}</span>
        </div>
        <div className="detail-item">
          <label>Patient ID</label>
          <span>{appointment.patientId}</span>
        </div>
        <div className="detail-item">
          <label>Doctor ID</label>
          <span>{appointment.doctorId}</span>
        </div>
        <div className="detail-item">
          <label>Created</label>
          <span>{appointment.createdAt.toLocaleString()}</span>
        </div>
        <div className="detail-item">
          <label>Last Updated</label>
          <span>{appointment.updatedAt.toLocaleString()}</span>
        </div>
      </div>

      {canTransition && (
        <div className="detail-actions">
          <h3>Actions</h3>
          <div className="action-buttons">
            {appointment.status.type === 'Requested' && (
              <>
                <button
                  className="action-button confirm"
                  onClick={() => onTransition('confirmed')}
                >
                  Confirm
                </button>
                <button
                  className="action-button cancel"
                  onClick={() => onTransition('cancelled')}
                >
                  Cancel
                </button>
              </>
            )}
            {appointment.status.type === 'Confirmed' && (
              <>
                <button
                  className="action-button start"
                  onClick={() => onTransition('in_progress')}
                >
                  Start
                </button>
                <button
                  className="action-button cancel"
                  onClick={() => onTransition('cancelled')}
                >
                  Cancel
                </button>
              </>
            )}
            {appointment.status.type === 'InProgress' && (
              <>
                <button
                  className="action-button complete"
                  onClick={() => onTransition('completed')}
                >
                  Complete
                </button>
                <button
                  className="action-button cancel"
                  onClick={() => onTransition('cancelled')}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
