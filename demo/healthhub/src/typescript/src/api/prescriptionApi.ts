/**
 * Prescription API functions.
 */

import { Result, isOk, ok } from '../algebraic/Result'
import { apiGet, apiPost, ApiError } from './client'
import { Prescription, PrescriptionApiResponse, fromApiResponse } from '../models/Prescription'

// Create prescription request type (matches backend CreatePrescriptionRequest)
export interface CreatePrescriptionRequest {
  readonly patient_id: string
  readonly doctor_id: string
  readonly medication: string
  readonly dosage: string
  readonly frequency: string
  readonly duration_days: number
  readonly refills_remaining: number
  readonly notes?: string
  readonly existing_medications?: string[]
}

// Convert API response to domain model
const toDomainModel = (result: Result<PrescriptionApiResponse, ApiError>): Result<Prescription, ApiError> =>
  isOk(result) ? ok<Prescription, ApiError>(fromApiResponse(result.value)) : result

// Convert list of API responses to domain models
const toDomainModels = (result: Result<PrescriptionApiResponse[], ApiError>): Result<Prescription[], ApiError> =>
  isOk(result) ? ok<Prescription[], ApiError>(result.value.map(fromApiResponse)) : result

// API functions
export const getPrescriptions = async (
  token: string
): Promise<Result<Prescription[], ApiError>> => {
  const result = await apiGet<PrescriptionApiResponse[]>('/prescriptions/', token)
  return toDomainModels(result)
}

export const getPrescription = async (
  prescriptionId: string,
  token: string
): Promise<Result<Prescription, ApiError>> => {
  const result = await apiGet<PrescriptionApiResponse>(`/prescriptions/${prescriptionId}`, token)
  return toDomainModel(result)
}

export const createPrescription = async (
  data: CreatePrescriptionRequest,
  token: string
): Promise<Result<Prescription, ApiError>> => {
  const result = await apiPost<PrescriptionApiResponse, CreatePrescriptionRequest>(
    '/prescriptions/',
    data,
    token
  )
  return toDomainModel(result)
}

export const getPrescriptionsByPatient = async (
  patientId: string,
  token: string
): Promise<Result<Prescription[], ApiError>> => {
  const result = await apiGet<PrescriptionApiResponse[]>(`/prescriptions/patient/${patientId}`, token)
  if (!isOk(result)) return result
  return ok<Prescription[], ApiError>(result.value.map(fromApiResponse))
}
