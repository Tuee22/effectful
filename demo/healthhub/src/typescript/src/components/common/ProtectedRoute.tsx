/**
 * ProtectedRoute component - Auth guard for protected pages.
 *
 * Uses auth state machine to determine access.
 */

import { ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { AuthState, UserRole } from '../../models/Auth'
import { Loading } from './Loading'
import './ProtectedRoute.css'

interface ProtectedRouteProps {
  readonly children: ReactNode
  readonly requiredRoles?: readonly UserRole[]
}

// Protection state ADT
type ProtectionState =
  | { type: 'CheckingAuth' }
  | { type: 'Authenticated'; role: UserRole }
  | { type: 'Redirecting'; reason: string }
  | { type: 'AccessDenied'; userRole: UserRole; requiredRoles: readonly UserRole[] }

// Pure function to derive protection state
const deriveProtectionState = (
  hasHydrated: boolean,
  authState: AuthState,
  requiredRoles: readonly UserRole[]
): ProtectionState => {
  // Still hydrating from localStorage
  if (!hasHydrated || authState.type === 'Hydrating') {
    return { type: 'CheckingAuth' }
  }

  // Not authenticated - redirect to login
  if (
    authState.type === 'Unauthenticated' ||
    authState.type === 'SessionExpired' ||
    authState.type === 'AuthenticationFailed' ||
    authState.type === 'RefreshDenied'
  ) {
    return { type: 'Redirecting', reason: 'Authentication required' }
  }

  // Authenticating in progress
  if (authState.type === 'Authenticating') {
    return { type: 'CheckingAuth' }
  }

  if (authState.type === 'Refreshing') {
    return { type: 'CheckingAuth' }
  }

  // Session restorable (need to re-auth)
  if (authState.type === 'SessionRestorable') {
    return { type: 'Redirecting', reason: 'Session expired' }
  }

  // Authenticated - check role
  if (authState.type === 'Authenticated') {
    // No role requirements - allow access
    if (requiredRoles.length === 0) {
      return { type: 'Authenticated', role: authState.role }
    }

    // Check if user has required role
    if (requiredRoles.includes(authState.role)) {
      return { type: 'Authenticated', role: authState.role }
    }

    // Access denied - wrong role
    return {
      type: 'AccessDenied',
      userRole: authState.role,
      requiredRoles,
    }
  }

  // Fallback - should never reach
  return { type: 'Redirecting', reason: 'Unknown auth state' }
}

export const ProtectedRoute = ({
  children,
  requiredRoles = [],
}: ProtectedRouteProps) => {
  const { authState, hasHydrated } = useAuth()
  const navigate = useNavigate()

  // Derive protection state (pure)
  const protectionState = useMemo(
    () => deriveProtectionState(hasHydrated, authState, requiredRoles),
    [hasHydrated, authState, requiredRoles]
  )

  // Timeout for stuck hydration
  const [hydrationTimeout, setHydrationTimeout] = useState(false)

  // Idempotency guard for redirect
  const redirectInitiatedRef = useRef(false)

  // Handle redirect side effect
  useEffect(() => {
    if (protectionState.type === 'Redirecting' && !redirectInitiatedRef.current) {
      redirectInitiatedRef.current = true
      navigate('/login', { replace: true })
    }

    if (protectionState.type !== 'Redirecting') {
      redirectInitiatedRef.current = false
    }
  }, [protectionState, navigate])

  // Timeout for stuck CheckingAuth
  useEffect(() => {
    if (protectionState.type === 'CheckingAuth') {
      const timer = setTimeout(() => {
        setHydrationTimeout(true)
      }, 5000)
      return () => clearTimeout(timer)
    } else {
      setHydrationTimeout(false)
    }
  }, [protectionState.type])

  // Render based on protection state
  switch (protectionState.type) {
    case 'CheckingAuth':
      if (hydrationTimeout) {
        return (
          <div className="protected-route-timeout">
            <div className="timeout-icon">!</div>
            <h2>Authentication Timeout</h2>
            <p>The application took too long to load your session.</p>
            <button onClick={() => window.location.reload()}>Retry</button>
          </div>
        )
      }
      return <Loading message="Checking authentication..." />

    case 'Redirecting':
      return <Loading message="Redirecting to login..." />

    case 'AccessDenied':
      return (
        <div className="protected-route-denied">
          <div className="denied-icon">!</div>
          <h2>Access Denied</h2>
          <p>You don't have permission to access this page.</p>
          <div className="role-info">
            <p>
              Your role: <strong>{protectionState.userRole}</strong>
            </p>
            <p>
              Required roles:{' '}
              <strong>{protectionState.requiredRoles.join(', ')}</strong>
            </p>
          </div>
          <button onClick={() => navigate('/')}>Go to Dashboard</button>
        </div>
      )

    case 'Authenticated':
      return <>{children}</>
  }
}
