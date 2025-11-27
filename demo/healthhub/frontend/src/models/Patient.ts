/**
 * Patient domain model.
 */

export interface Patient {
  readonly id: string
  readonly userId: string
  readonly firstName: string
  readonly lastName: string
  readonly dateOfBirth: Date
  readonly bloodType: string | null
  readonly allergies: readonly string[]
  readonly insuranceId: string | null
  readonly emergencyContact: string
  readonly phone: string | null
  readonly address: string | null
}

// API response type (matches backend)
export interface PatientApiResponse {
  readonly id: string
  readonly user_id: string
  readonly first_name: string
  readonly last_name: string
  readonly date_of_birth: string
  readonly blood_type: string | null
  readonly allergies: string[]
  readonly insurance_id: string | null
  readonly emergency_contact: string
  readonly phone: string | null
  readonly address: string | null
}

// Converter from API response to domain model
export const fromApiResponse = (response: PatientApiResponse): Patient => ({
  id: response.id,
  userId: response.user_id,
  firstName: response.first_name,
  lastName: response.last_name,
  dateOfBirth: new Date(response.date_of_birth),
  bloodType: response.blood_type,
  allergies: response.allergies,
  insuranceId: response.insurance_id,
  emergencyContact: response.emergency_contact,
  phone: response.phone,
  address: response.address,
})

// Display helpers
export const getFullName = (patient: Patient): string =>
  `${patient.firstName} ${patient.lastName}`

export const formatDateOfBirth = (patient: Patient): string =>
  patient.dateOfBirth.toLocaleDateString()

export const getAge = (patient: Patient): number => {
  const today = new Date()
  const birthDate = patient.dateOfBirth
  let age = today.getFullYear() - birthDate.getFullYear()
  const monthDiff = today.getMonth() - birthDate.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--
  }
  return age
}
