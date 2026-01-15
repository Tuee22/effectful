/**
 * Patient API functions.
 */

import { Result, isOk, ok } from '../algebraic/Result'
import { apiGet, apiPost, apiPut, apiDelete, ApiError } from './client'
import { Patient, PatientApiResponse, fromApiResponse } from '../models/Patient'

// Create patient request type
export interface CreatePatientRequest {
  readonly user_id: string
  readonly first_name: string
  readonly last_name: string
  readonly date_of_birth: string
  readonly blood_type?: string
  readonly allergies?: string[]
  readonly insurance_id?: string
  readonly emergency_contact: string
  readonly phone?: string
  readonly address?: string
}

// Update patient request type
export interface UpdatePatientRequest {
  readonly first_name?: string
  readonly last_name?: string
  readonly blood_type?: string
  readonly allergies?: string[]
  readonly insurance_id?: string
  readonly emergency_contact?: string
  readonly phone?: string
  readonly address?: string
}

// Convert API response to domain model
const toDomainModel = (result: Result<PatientApiResponse, ApiError>): Result<Patient, ApiError> =>
  isOk(result) ? ok<Patient, ApiError>(fromApiResponse(result.value)) : result

// Convert list of API responses to domain models
const toDomainModels = (result: Result<PatientApiResponse[], ApiError>): Result<Patient[], ApiError> =>
  isOk(result) ? ok<Patient[], ApiError>(result.value.map(fromApiResponse)) : result

// API functions
export const getPatients = async (
  token: string
): Promise<Result<Patient[], ApiError>> => {
  const result = await apiGet<PatientApiResponse[]>('/patients/', token)
  return toDomainModels(result)
}

export const getPatient = async (
  patientId: string,
  token: string
): Promise<Result<Patient, ApiError>> => {
  const result = await apiGet<PatientApiResponse>(`/patients/${patientId}`, token)
  return toDomainModel(result)
}

export const getPatientByUserId = async (
  userId: string,
  token: string
): Promise<Result<Patient, ApiError>> => {
  const result = await apiGet<PatientApiResponse>(`/patients/by-user/${userId}`, token)
  return toDomainModel(result)
}

export const createPatient = async (
  data: CreatePatientRequest,
  token: string
): Promise<Result<Patient, ApiError>> => {
  const result = await apiPost<PatientApiResponse, CreatePatientRequest>(
    '/patients/',
    data,
    token
  )
  return toDomainModel(result)
}

export const updatePatient = async (
  patientId: string,
  data: UpdatePatientRequest,
  token: string
): Promise<Result<Patient, ApiError>> => {
  const result = await apiPut<PatientApiResponse, UpdatePatientRequest>(
    `/patients/${patientId}`,
    data,
    token
  )
  return toDomainModel(result)
}

export const deletePatient = (
  patientId: string,
  token: string
): Promise<Result<void, ApiError>> =>
  apiDelete(`/patients/${patientId}`, token)
