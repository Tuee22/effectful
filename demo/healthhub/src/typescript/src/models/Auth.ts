/**
 * Authentication domain models with algebraic data types.
 *
 * 7-state auth machine making illegal states unrepresentable.
 */

// User role enum
export type UserRole = 'patient' | 'doctor' | 'admin'

// Auth state machine (7 states)
export type AuthState =
  | Hydrating
  | Unauthenticated
  | Authenticating
  | SessionRestorable
  | Refreshing
  | Authenticated
  | SessionExpired
  | RefreshDenied
  | AuthenticationFailed

export interface Hydrating {
  readonly type: 'Hydrating'
}

export interface Unauthenticated {
  readonly type: 'Unauthenticated'
}

export interface Authenticating {
  readonly type: 'Authenticating'
  readonly email: string
}

export interface Refreshing {
  readonly type: 'Refreshing'
  readonly reason: 'missing_access' | 'expired'
}

export interface SessionRestorable {
  readonly type: 'SessionRestorable'
  readonly userId: string
  readonly email: string
  readonly role: UserRole
  readonly lastActivity: Date
}

export interface Authenticated {
  readonly type: 'Authenticated'
  readonly accessToken: string
  readonly userId: string
  readonly email: string
  readonly role: UserRole
  readonly expiresAt: Date
}

export interface SessionExpired {
  readonly type: 'SessionExpired'
  readonly userId: string
  readonly email: string
  readonly expiredAt: Date
}

export interface AuthenticationFailed {
  readonly type: 'AuthenticationFailed'
  readonly email: string
  readonly error: AuthError
  readonly attemptedAt: Date
}

export interface RefreshDenied {
  readonly type: 'RefreshDenied'
  readonly reason: string
  readonly attemptedAt: Date
}

// Auth error types
export type AuthError =
  | InvalidCredentials
  | AccountLocked
  | NetworkError
  | UnknownAuthError

export interface InvalidCredentials {
  readonly type: 'InvalidCredentials'
  readonly message: string
}

export interface AccountLocked {
  readonly type: 'AccountLocked'
  readonly unlockAt: Date
}

export interface NetworkError {
  readonly type: 'NetworkError'
  readonly message: string
}

export interface UnknownAuthError {
  readonly type: 'UnknownAuthError'
  readonly message: string
}

// Constructors
export const hydrating = (): AuthState => ({ type: 'Hydrating' })

export const unauthenticated = (): AuthState => ({ type: 'Unauthenticated' })

export const authenticating = (email: string): AuthState => ({
  type: 'Authenticating',
  email,
})

export const refreshing = (reason: Refreshing['reason']): AuthState => ({
  type: 'Refreshing',
  reason,
})

export const sessionRestorable = (
  userId: string,
  email: string,
  role: UserRole,
  lastActivity: Date
): AuthState => ({
  type: 'SessionRestorable',
  userId,
  email,
  role,
  lastActivity,
})

export const authenticated = (
  accessToken: string,
  userId: string,
  email: string,
  role: UserRole,
  expiresAt: Date
): AuthState => ({
  type: 'Authenticated',
  accessToken,
  userId,
  email,
  role,
  expiresAt,
})

export const sessionExpired = (
  userId: string,
  email: string,
  expiredAt: Date
): AuthState => ({
  type: 'SessionExpired',
  userId,
  email,
  expiredAt,
})

export const authenticationFailed = (
  email: string,
  error: AuthError,
  attemptedAt: Date
): AuthState => ({
  type: 'AuthenticationFailed',
  email,
  error,
  attemptedAt,
})

export const refreshDenied = (reason: string, attemptedAt: Date): AuthState => ({
  type: 'RefreshDenied',
  reason,
  attemptedAt,
})

// Error constructors
export const invalidCredentials = (message: string): AuthError => ({
  type: 'InvalidCredentials',
  message,
})

export const accountLocked = (unlockAt: Date): AuthError => ({
  type: 'AccountLocked',
  unlockAt,
})

export const networkError = (message: string): AuthError => ({
  type: 'NetworkError',
  message,
})

export const unknownAuthError = (message: string): AuthError => ({
  type: 'UnknownAuthError',
  message,
})

// Type guards
export const isHydrating = (state: AuthState): state is Hydrating =>
  state.type === 'Hydrating'

export const isUnauthenticated = (state: AuthState): state is Unauthenticated =>
  state.type === 'Unauthenticated'

export const isAuthenticating = (state: AuthState): state is Authenticating =>
  state.type === 'Authenticating'

export const isSessionRestorable = (state: AuthState): state is SessionRestorable =>
  state.type === 'SessionRestorable'

export const isRefreshing = (state: AuthState): state is Refreshing =>
  state.type === 'Refreshing'

export const isAuthenticated = (state: AuthState): state is Authenticated =>
  state.type === 'Authenticated'

export const isSessionExpired = (state: AuthState): state is SessionExpired =>
  state.type === 'SessionExpired'

export const isAuthenticationFailed = (state: AuthState): state is AuthenticationFailed =>
  state.type === 'AuthenticationFailed'

export const isRefreshDenied = (state: AuthState): state is RefreshDenied =>
  state.type === 'RefreshDenied'

// Utility functions
export const isLoggedIn = (state: AuthState): boolean =>
  state.type === 'Authenticated'

export const shouldRedirectToLogin = (state: AuthState): boolean =>
  state.type === 'Unauthenticated' ||
  state.type === 'SessionExpired' ||
  state.type === 'AuthenticationFailed' ||
  state.type === 'RefreshDenied'

export const getErrorMessage = (error: AuthError): string => {
  switch (error.type) {
    case 'InvalidCredentials':
      return error.message
    case 'AccountLocked':
      return `Account locked until ${error.unlockAt.toLocaleString()}`
    case 'NetworkError':
      return `Network error: ${error.message}`
    case 'UnknownAuthError':
      return `An error occurred: ${error.message}`
  }
}
