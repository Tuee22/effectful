/**
 * useAuth hook - Convenience wrapper for auth store.
 */

import { useAuthStore } from '../stores/authStore'
import { isAuthenticated, isHydrating, shouldRedirectToLogin } from '../models/Auth'
import { useEffect } from 'react'

export const useAuth = () => {
  const authState = useAuthStore((state) => state.authState)
  const login = useAuthStore((state) => state.login)
  const logout = useAuthStore((state) => state.logout)
  const clearError = useAuthStore((state) => state.clearError)
  const hasHydrated = useAuthStore((state) => state.hasHydrated())
  const getToken = useAuthStore((state) => state.getToken)
  const getUserId = useAuthStore((state) => state.getUserId)
  const getRole = useAuthStore((state) => state.getRole)
  const bootstrap = useAuthStore((state) => state.bootstrap)

  useEffect(() => {
    if (!hasHydrated || isHydrating(authState)) {
      void bootstrap()
    }
  }, [authState, bootstrap, hasHydrated])

  return {
    // State
    authState,
    hasHydrated,

    // Computed
    isAuthenticated: isAuthenticated(authState),
    isHydrating: isHydrating(authState),
    shouldRedirectToLogin: shouldRedirectToLogin(authState),
    token: getToken(),
    userId: getUserId(),
    role: getRole(),

    // Actions
    login,
    logout,
    clearError,
  }
}
