/**
 * Invoice API functions.
 */

import { Result, isOk, ok } from '../algebraic/Result'
import { apiGet, apiPost, apiPatch, ApiError } from './client'
import {
  Invoice,
  InvoiceApiResponse,
  InvoiceWithLineItems,
  InvoiceWithLineItemsApiResponse,
  LineItem,
  LineItemApiResponse,
  fromApiResponse,
  lineItemFromApiResponse,
  invoiceWithLineItemsFromApiResponse,
  InvoiceStatus,
} from '../models/Invoice'

// Create invoice request type
export interface CreateInvoiceRequest {
  readonly patient_id: string
  readonly appointment_id?: string
  readonly due_date?: string
}

// Create line item request type
export interface CreateLineItemRequest {
  readonly description: string
  readonly quantity?: number
  readonly unit_price: number
}

// Update invoice status request type
export interface UpdateInvoiceStatusRequest {
  readonly status: InvoiceStatus
}

// Convert API response to domain model
const toDomainModel = (result: Result<InvoiceApiResponse, ApiError>): Result<Invoice, ApiError> =>
  isOk(result) ? ok<Invoice, ApiError>(fromApiResponse(result.value)) : result

// Convert list of API responses to domain models
const toDomainModels = (result: Result<InvoiceApiResponse[], ApiError>): Result<Invoice[], ApiError> =>
  isOk(result) ? ok<Invoice[], ApiError>(result.value.map(fromApiResponse)) : result

// API functions
export const getInvoices = async (
  token: string
): Promise<Result<Invoice[], ApiError>> => {
  const result = await apiGet<InvoiceApiResponse[]>('/invoices/', token)
  return toDomainModels(result)
}

export const getInvoice = async (
  invoiceId: string,
  token: string
): Promise<Result<InvoiceWithLineItems, ApiError>> => {
  const result = await apiGet<InvoiceWithLineItemsApiResponse>(`/invoices/${invoiceId}`, token)
  if (!isOk(result)) return result
  return ok<InvoiceWithLineItems, ApiError>(invoiceWithLineItemsFromApiResponse(result.value))
}

export const createInvoice = async (
  data: CreateInvoiceRequest,
  token: string
): Promise<Result<Invoice, ApiError>> => {
  const result = await apiPost<InvoiceApiResponse, CreateInvoiceRequest>(
    '/invoices/',
    data,
    token
  )
  return toDomainModel(result)
}

export const addLineItem = async (
  invoiceId: string,
  data: CreateLineItemRequest,
  token: string
): Promise<Result<LineItem, ApiError>> => {
  const result = await apiPost<LineItemApiResponse, CreateLineItemRequest>(
    `/invoices/${invoiceId}/line-items`,
    data,
    token
  )
  if (!isOk(result)) return result
  return ok<LineItem, ApiError>(lineItemFromApiResponse(result.value))
}

export const updateInvoiceStatus = async (
  invoiceId: string,
  status: InvoiceStatus,
  token: string
): Promise<Result<Invoice, ApiError>> => {
  const result = await apiPatch<InvoiceApiResponse, UpdateInvoiceStatusRequest>(
    `/invoices/${invoiceId}/status`,
    { status },
    token
  )
  return toDomainModel(result)
}

export const getInvoicesByPatient = async (
  patientId: string,
  token: string
): Promise<Result<Invoice[], ApiError>> => {
  const result = await apiGet<InvoiceApiResponse[]>(`/invoices/patient/${patientId}`, token)
  return toDomainModels(result)
}
