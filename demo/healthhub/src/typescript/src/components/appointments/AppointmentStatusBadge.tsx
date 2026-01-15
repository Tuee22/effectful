/**
 * AppointmentStatusBadge component - Status indicator badge.
 */

import { AppointmentStatus, getStatusLabel, getStatusColor } from '../../models/Appointment'
import './AppointmentStatusBadge.css'

interface AppointmentStatusBadgeProps {
  readonly status: AppointmentStatus
}

export const AppointmentStatusBadge = ({ status }: AppointmentStatusBadgeProps) => {
  const label = getStatusLabel(status)
  const color = getStatusColor(status)

  return (
    <span
      className="appointment-status-badge"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  )
}
