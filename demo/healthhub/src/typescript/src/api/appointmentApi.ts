/**
 * Appointment API functions.
 */

import { Result, isOk, ok } from '../algebraic/Result'
import { apiGet, apiPost, ApiError } from './client'
import { Appointment, AppointmentApiResponse, fromApiResponse } from '../models/Appointment'

// Create appointment request type
export interface CreateAppointmentRequest {
  readonly patient_id: string
  readonly doctor_id: string
  readonly requested_time?: string
  readonly reason: string
}

// Transition status request type
export interface TransitionStatusRequest {
  readonly new_status: string
  readonly actor_id: string
}

// Transition status response
export interface TransitionStatusResponse {
  readonly status: string
  readonly message: string
}

// Convert API response to domain model
const toDomainModel = (result: Result<AppointmentApiResponse, ApiError>): Result<Appointment, ApiError> =>
  isOk(result) ? ok<Appointment, ApiError>(fromApiResponse(result.value)) : result

// Convert list of API responses to domain models
const toDomainModels = (result: Result<AppointmentApiResponse[], ApiError>): Result<Appointment[], ApiError> =>
  isOk(result) ? ok<Appointment[], ApiError>(result.value.map(fromApiResponse)) : result

// API functions
export const getAppointments = async (
  token: string,
  statusFilter?: string
): Promise<Result<Appointment[], ApiError>> => {
  const url = statusFilter ? `/appointments/?status_filter=${statusFilter}` : '/appointments/'
  const result = await apiGet<AppointmentApiResponse[]>(url, token)
  return toDomainModels(result)
}

export const getAppointment = async (
  appointmentId: string,
  token: string
): Promise<Result<Appointment, ApiError>> => {
  const result = await apiGet<AppointmentApiResponse>(`/appointments/${appointmentId}`, token)
  return toDomainModel(result)
}

export const createAppointment = async (
  data: CreateAppointmentRequest,
  token: string
): Promise<Result<Appointment, ApiError>> => {
  const result = await apiPost<AppointmentApiResponse, CreateAppointmentRequest>(
    '/appointments/',
    data,
    token
  )
  return toDomainModel(result)
}

export const transitionAppointmentStatus = (
  appointmentId: string,
  newStatus: string,
  actorId: string,
  token: string
): Promise<Result<TransitionStatusResponse, ApiError>> =>
  apiPost<TransitionStatusResponse, TransitionStatusRequest>(
    `/appointments/${appointmentId}/transition`,
    {
      new_status: newStatus,
      actor_id: actorId,
    },
    token
  )
