/**
 * Authentication API functions.
 */

import { Result } from '../algebraic/Result'
import { apiPost, ApiError } from './client'

// Login request/response types (match backend)
export interface LoginRequest {
  readonly email: string
  readonly password: string
}

export interface LoginResponse {
  readonly access_token: string
  readonly token_type: string
  readonly user_id: string
  readonly email: string
  readonly role: 'patient' | 'doctor' | 'admin'
}

// Register request/response types
export interface RegisterRequest {
  readonly email: string
  readonly password: string
  readonly role: 'patient' | 'doctor' | 'admin'
}

export interface RegisterResponse {
  readonly user_id: string
  readonly email: string
  readonly role: string
  readonly message: string
}

// API functions
export const login = (
  email: string,
  password: string
): Promise<Result<LoginResponse, ApiError>> =>
  apiPost<LoginResponse, LoginRequest>('/auth/login', { email, password })

export const register = (
  email: string,
  password: string,
  role: 'patient' | 'doctor' | 'admin'
): Promise<Result<RegisterResponse, ApiError>> =>
  apiPost<RegisterResponse, RegisterRequest>('/auth/register', {
    email,
    password,
    role,
  })
