/**
 * Lab Result domain model.
 */

export interface LabResult {
  readonly id: string
  readonly patientId: string
  readonly doctorId: string
  readonly testType: string
  readonly resultData: Record<string, string>
  readonly critical: boolean
  readonly reviewedByDoctor: boolean
  readonly doctorNotes: string | null
  readonly createdAt: Date
}

// API response type (matches backend LabResultResponse)
export interface LabResultApiResponse {
  readonly id: string
  readonly patient_id: string
  readonly doctor_id: string
  readonly test_type: string
  readonly result_data: Record<string, string>
  readonly critical: boolean
  readonly reviewed_by_doctor: boolean
  readonly doctor_notes: string | null
  readonly created_at: string
}

// Converter from API response to domain model
export const fromApiResponse = (response: LabResultApiResponse): LabResult => ({
  id: response.id,
  patientId: response.patient_id,
  doctorId: response.doctor_id,
  testType: response.test_type,
  resultData: response.result_data,
  critical: response.critical,
  reviewedByDoctor: response.reviewed_by_doctor,
  doctorNotes: response.doctor_notes,
  createdAt: new Date(response.created_at),
})

// Display helpers
export const getStatusLabel = (labResult: LabResult): string =>
  labResult.critical ? 'Critical' : labResult.reviewedByDoctor ? 'Reviewed' : 'Pending Review'

export const getStatusColor = (labResult: LabResult): string => {
  if (labResult.critical) return '#ef4444' // Red
  if (labResult.reviewedByDoctor) return '#10b981' // Green
  return '#f59e0b' // Amber
}

export const formatDate = (date: Date): string =>
  date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
