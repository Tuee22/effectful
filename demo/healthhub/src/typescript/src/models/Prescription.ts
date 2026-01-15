/**
 * Prescription domain model.
 */

export interface Prescription {
  readonly id: string
  readonly patientId: string
  readonly doctorId: string
  readonly medication: string
  readonly dosage: string
  readonly frequency: string
  readonly durationDays: number
  readonly refillsRemaining: number
  readonly notes: string | null
  readonly createdAt: Date
  readonly expiresAt: Date
}

export type PrescriptionStatus = 'active' | 'completed' | 'cancelled'

// API response type (matches backend PrescriptionResponse)
export interface PrescriptionApiResponse {
  readonly id: string
  readonly patient_id: string
  readonly doctor_id: string
  readonly medication: string
  readonly dosage: string
  readonly frequency: string
  readonly duration_days: number
  readonly refills_remaining: number
  readonly notes: string | null
  readonly created_at: string
  readonly expires_at: string
}

// Converter from API response to domain model
export const fromApiResponse = (response: PrescriptionApiResponse): Prescription => ({
  id: response.id,
  patientId: response.patient_id,
  doctorId: response.doctor_id,
  medication: response.medication,
  dosage: response.dosage,
  frequency: response.frequency,
  durationDays: response.duration_days,
  refillsRemaining: response.refills_remaining,
  notes: response.notes,
  createdAt: new Date(response.created_at),
  expiresAt: new Date(response.expires_at),
})

// Compute status from prescription expiration
export const getStatus = (prescription: Prescription): PrescriptionStatus =>
  prescription.expiresAt > new Date() ? 'active' : 'completed'

// Display helpers
export const getStatusLabel = (status: PrescriptionStatus): string => {
  switch (status) {
    case 'active':
      return 'Active'
    case 'completed':
      return 'Completed'
    case 'cancelled':
      return 'Cancelled'
  }
}

export const getStatusColor = (status: PrescriptionStatus): string => {
  switch (status) {
    case 'active':
      return '#10b981' // Green
    case 'completed':
      return '#6b7280' // Gray
    case 'cancelled':
      return '#ef4444' // Red
  }
}
