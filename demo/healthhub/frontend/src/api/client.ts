/**
 * API client with Result type for error handling.
 *
 * All API calls return Result<T, ApiError> instead of throwing.
 */

import { Result, ok, err } from '../algebraic/Result'

// API error type
export interface ApiError {
  readonly status: number
  readonly message: string
  readonly detail?: string
}

// Base URL - proxied through Vite to backend
const BASE_URL = '/api'

// Generic GET request
export const apiGet = async <T>(
  path: string,
  token?: string
): Promise<Result<T, ApiError>> => {
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'GET',
      headers,
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return err({
        status: response.status,
        message: data.detail || response.statusText,
        detail: data.detail,
      })
    }

    const data = await response.json()
    return ok(data as T)
  } catch (error) {
    return err({
      status: 0,
      message: error instanceof Error ? error.message : 'Network error',
    })
  }
}

// Generic POST request
export const apiPost = async <T, B>(
  path: string,
  body: B,
  token?: string
): Promise<Result<T, ApiError>> => {
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return err({
        status: response.status,
        message: data.detail || response.statusText,
        detail: data.detail,
      })
    }

    const data = await response.json()
    return ok(data as T)
  } catch (error) {
    return err({
      status: 0,
      message: error instanceof Error ? error.message : 'Network error',
    })
  }
}

// Generic PUT request
export const apiPut = async <T, B>(
  path: string,
  body: B,
  token?: string
): Promise<Result<T, ApiError>> => {
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return err({
        status: response.status,
        message: data.detail || response.statusText,
        detail: data.detail,
      })
    }

    const data = await response.json()
    return ok(data as T)
  } catch (error) {
    return err({
      status: 0,
      message: error instanceof Error ? error.message : 'Network error',
    })
  }
}

// Generic PATCH request
export const apiPatch = async <T, B>(
  path: string,
  body: B,
  token?: string
): Promise<Result<T, ApiError>> => {
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return err({
        status: response.status,
        message: data.detail || response.statusText,
        detail: data.detail,
      })
    }

    const data = await response.json()
    return ok(data as T)
  } catch (error) {
    return err({
      status: 0,
      message: error instanceof Error ? error.message : 'Network error',
    })
  }
}

// Generic DELETE request
export const apiDelete = async (
  path: string,
  token?: string
): Promise<Result<void, ApiError>> => {
  try {
    const headers: HeadersInit = {}

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers,
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return err({
        status: response.status,
        message: data.detail || response.statusText,
        detail: data.detail,
      })
    }

    return ok(undefined)
  } catch (error) {
    return err({
      status: 0,
      message: error instanceof Error ? error.message : 'Network error',
    })
  }
}
