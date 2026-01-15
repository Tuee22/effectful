/**
 * Appointment domain model with status state machine.
 */

// Appointment status ADT (state machine)
export type AppointmentStatus =
  | Requested
  | Confirmed
  | InProgress
  | Completed
  | Cancelled

export interface Requested {
  readonly type: 'Requested'
  readonly requestedAt: Date
}

export interface Confirmed {
  readonly type: 'Confirmed'
  readonly confirmedAt: Date
  readonly scheduledTime: Date
}

export interface InProgress {
  readonly type: 'InProgress'
  readonly startedAt: Date
}

export interface Completed {
  readonly type: 'Completed'
  readonly completedAt: Date
  readonly notes: string
}

export interface Cancelled {
  readonly type: 'Cancelled'
  readonly cancelledAt: Date
  readonly cancelledBy: 'patient' | 'doctor' | 'system'
  readonly reason: string
}

// Appointment domain model
export interface Appointment {
  readonly id: string
  readonly patientId: string
  readonly doctorId: string
  readonly status: AppointmentStatus
  readonly reason: string
  readonly createdAt: Date
  readonly updatedAt: Date
}

// API response type (matches backend - flattened status)
export interface AppointmentApiResponse {
  readonly id: string
  readonly patient_id: string
  readonly doctor_id: string
  readonly status: string // "requested" | "confirmed" | "in_progress" | "completed" | "cancelled"
  readonly reason: string
  readonly created_at: string
  readonly updated_at: string
}

// Status constructors
export const requested = (requestedAt: Date = new Date()): AppointmentStatus => ({
  type: 'Requested',
  requestedAt,
})

export const confirmed = (
  scheduledTime: Date,
  confirmedAt: Date = new Date()
): AppointmentStatus => ({
  type: 'Confirmed',
  confirmedAt,
  scheduledTime,
})

export const inProgress = (startedAt: Date = new Date()): AppointmentStatus => ({
  type: 'InProgress',
  startedAt,
})

export const completed = (
  notes: string,
  completedAt: Date = new Date()
): AppointmentStatus => ({
  type: 'Completed',
  completedAt,
  notes,
})

export const cancelled = (
  cancelledBy: 'patient' | 'doctor' | 'system',
  reason: string,
  cancelledAt: Date = new Date()
): AppointmentStatus => ({
  type: 'Cancelled',
  cancelledAt,
  cancelledBy,
  reason,
})

// Type guards
export const isRequested = (status: AppointmentStatus): status is Requested =>
  status.type === 'Requested'

export const isConfirmed = (status: AppointmentStatus): status is Confirmed =>
  status.type === 'Confirmed'

export const isInProgress = (status: AppointmentStatus): status is InProgress =>
  status.type === 'InProgress'

export const isCompleted = (status: AppointmentStatus): status is Completed =>
  status.type === 'Completed'

export const isCancelled = (status: AppointmentStatus): status is Cancelled =>
  status.type === 'Cancelled'

// Check if appointment is terminal (no further transitions)
export const isTerminal = (status: AppointmentStatus): boolean =>
  status.type === 'Completed' || status.type === 'Cancelled'

// Convert API status string to ADT
const parseStatus = (statusStr: string): AppointmentStatus => {
  switch (statusStr) {
    case 'requested':
      return requested()
    case 'confirmed':
      return confirmed(new Date())
    case 'in_progress':
      return inProgress()
    case 'completed':
      return completed('')
    case 'cancelled':
      return cancelled('system', 'Unknown reason')
    default:
      return requested() // Default fallback
  }
}

// Converter from API response to domain model
export const fromApiResponse = (response: AppointmentApiResponse): Appointment => ({
  id: response.id,
  patientId: response.patient_id,
  doctorId: response.doctor_id,
  status: parseStatus(response.status),
  reason: response.reason,
  createdAt: new Date(response.created_at),
  updatedAt: new Date(response.updated_at),
})

// Display helpers
export const getStatusLabel = (status: AppointmentStatus): string => {
  switch (status.type) {
    case 'Requested':
      return 'Requested'
    case 'Confirmed':
      return 'Confirmed'
    case 'InProgress':
      return 'In Progress'
    case 'Completed':
      return 'Completed'
    case 'Cancelled':
      return 'Cancelled'
  }
}

export const getStatusColor = (status: AppointmentStatus): string => {
  switch (status.type) {
    case 'Requested':
      return '#f59e0b' // Amber
    case 'Confirmed':
      return '#3b82f6' // Blue
    case 'InProgress':
      return '#8b5cf6' // Purple
    case 'Completed':
      return '#10b981' // Green
    case 'Cancelled':
      return '#ef4444' // Red
  }
}
