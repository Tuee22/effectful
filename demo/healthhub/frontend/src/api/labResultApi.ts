/**
 * Lab Result API functions.
 */

import { Result, isOk, ok } from '../algebraic/Result'
import { apiGet, apiPost, ApiError } from './client'
import { LabResult, LabResultApiResponse, fromApiResponse } from '../models/LabResult'

// Create lab result request type
export interface CreateLabResultRequest {
  readonly patient_id: string
  readonly doctor_id: string
  readonly test_type: string
  readonly result_data: Record<string, string>
  readonly critical?: boolean
  readonly doctor_notes?: string
}

// Review lab result request type
export interface ReviewLabResultRequest {
  readonly doctor_notes?: string
}

// Convert API response to domain model
const toDomainModel = (result: Result<LabResultApiResponse, ApiError>): Result<LabResult, ApiError> =>
  isOk(result) ? ok<LabResult, ApiError>(fromApiResponse(result.value)) : result

// Convert list of API responses to domain models
const toDomainModels = (result: Result<LabResultApiResponse[], ApiError>): Result<LabResult[], ApiError> =>
  isOk(result) ? ok<LabResult[], ApiError>(result.value.map(fromApiResponse)) : result

// API functions
export const getLabResults = async (
  token: string
): Promise<Result<LabResult[], ApiError>> => {
  const result = await apiGet<LabResultApiResponse[]>('/lab-results/', token)
  return toDomainModels(result)
}

export const getLabResult = async (
  labResultId: string,
  token: string
): Promise<Result<LabResult, ApiError>> => {
  const result = await apiGet<LabResultApiResponse>(`/lab-results/${labResultId}`, token)
  return toDomainModel(result)
}

export const createLabResult = async (
  data: CreateLabResultRequest,
  token: string
): Promise<Result<LabResult, ApiError>> => {
  const result = await apiPost<LabResultApiResponse, CreateLabResultRequest>(
    '/lab-results/',
    data,
    token
  )
  return toDomainModel(result)
}

export const reviewLabResult = async (
  labResultId: string,
  data: ReviewLabResultRequest,
  token: string
): Promise<Result<LabResult, ApiError>> => {
  const result = await apiPost<LabResultApiResponse, ReviewLabResultRequest>(
    `/lab-results/${labResultId}/review`,
    data,
    token
  )
  return toDomainModel(result)
}

export const getLabResultsByPatient = async (
  patientId: string,
  token: string
): Promise<Result<LabResult[], ApiError>> => {
  const result = await apiGet<LabResultApiResponse[]>(`/lab-results/patient/${patientId}`, token)
  return toDomainModels(result)
}
