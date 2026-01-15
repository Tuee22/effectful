/**
 * Doctor domain model.
 */

export interface Doctor {
  readonly id: string
  readonly userId: string
  readonly firstName: string
  readonly lastName: string
  readonly specialization: string
  readonly licenseNumber: string
  readonly canPrescribe: boolean
  readonly phone: string | null
  readonly email: string
}

// API response type (matches backend)
export interface DoctorApiResponse {
  readonly id: string
  readonly user_id: string
  readonly first_name: string
  readonly last_name: string
  readonly specialization: string
  readonly license_number: string
  readonly can_prescribe: boolean
  readonly phone: string | null
  readonly email: string
}

// Converter from API response to domain model
export const fromApiResponse = (response: DoctorApiResponse): Doctor => ({
  id: response.id,
  userId: response.user_id,
  firstName: response.first_name,
  lastName: response.last_name,
  specialization: response.specialization,
  licenseNumber: response.license_number,
  canPrescribe: response.can_prescribe,
  phone: response.phone,
  email: response.email,
})

// Display helpers
export const getFullName = (doctor: Doctor): string =>
  `Dr. ${doctor.firstName} ${doctor.lastName}`

export const getDisplayTitle = (doctor: Doctor): string =>
  `${getFullName(doctor)} - ${doctor.specialization}`
