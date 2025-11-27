/**
 * Domain models for HealthHub frontend.
 *
 * Re-exports all domain types and utilities.
 * Uses explicit re-exports to avoid name conflicts.
 */

// Auth types and utilities
export type { AuthState, Hydrating, Unauthenticated, Authenticating, SessionRestorable, Authenticated, SessionExpired, AuthenticationFailed, UserRole, AuthError, InvalidCredentials, AccountLocked, NetworkError, UnknownAuthError } from './Auth'
export { hydrating, unauthenticated, authenticating, sessionRestorable, authenticated, sessionExpired, authenticationFailed, invalidCredentials, accountLocked, networkError, unknownAuthError, isHydrating, isUnauthenticated, isAuthenticating, isSessionRestorable, isAuthenticated, isSessionExpired, isAuthenticationFailed, isLoggedIn, shouldRedirectToLogin, getErrorMessage } from './Auth'

// Patient types and utilities
export type { Patient, PatientApiResponse } from './Patient'
export { fromApiResponse as patientFromApiResponse, getFullName as patientGetFullName, formatDateOfBirth, getAge } from './Patient'

// Doctor types and utilities
export type { Doctor, DoctorApiResponse } from './Doctor'
export { fromApiResponse as doctorFromApiResponse, getFullName as doctorGetFullName, getDisplayTitle } from './Doctor'

// Appointment types and utilities
export type { Appointment, AppointmentApiResponse, AppointmentStatus, Requested, Confirmed, InProgress, Completed, Cancelled } from './Appointment'
export { fromApiResponse as appointmentFromApiResponse, requested, confirmed, inProgress, completed, cancelled, isRequested, isConfirmed, isInProgress, isCompleted, isCancelled, isTerminal, getStatusLabel, getStatusColor } from './Appointment'

// Prescription types and utilities
export type { Prescription, PrescriptionApiResponse, PrescriptionStatus } from './Prescription'
export { fromApiResponse as prescriptionFromApiResponse, getStatus as prescriptionGetStatus, getStatusLabel as prescriptionGetStatusLabel, getStatusColor as prescriptionGetStatusColor } from './Prescription'

// Lab Result types and utilities
export type { LabResult, LabResultApiResponse } from './LabResult'
export { fromApiResponse as labResultFromApiResponse, getStatusLabel as labResultGetStatusLabel, getStatusColor as labResultGetStatusColor, formatDate as labResultFormatDate } from './LabResult'

// Invoice types and utilities
export type { Invoice, InvoiceApiResponse, InvoiceStatus, LineItem, LineItemApiResponse, InvoiceWithLineItems, InvoiceWithLineItemsApiResponse } from './Invoice'
export { fromApiResponse as invoiceFromApiResponse, lineItemFromApiResponse, invoiceWithLineItemsFromApiResponse, getStatusLabel as invoiceGetStatusLabel, getStatusColor as invoiceGetStatusColor, formatCurrency as invoiceFormatCurrency, formatDate as invoiceFormatDate } from './Invoice'
