/**
 * Authentication Store using Zustand + Immer + Persist
 *
 * Manages authentication state with type-safe algebraic data types.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import {
  AuthState,
  UserRole,
  hydrating,
  unauthenticated,
  authenticating,
  authenticated,
  authenticationFailed,
  invalidCredentials,
  networkError,
  unknownAuthError,
  isAuthenticated,
  isHydrating,
} from '../models/Auth'
import { Result, isOk } from '../algebraic/Result'
import { login as apiLogin, LoginResponse } from '../api/authApi'
import { ApiError } from '../api/client'

export interface AuthStore {
  // State
  authState: AuthState
  _hasHydrated: boolean

  // Actions
  login: (email: string, password: string) => Promise<Result<LoginResponse, ApiError>>
  logout: () => void
  clearError: () => void

  // Selectors
  isLoggedIn: () => boolean
  getToken: () => string | null
  getUserId: () => string | null
  getRole: () => UserRole | null
  hasHydrated: () => boolean
}

export const useAuthStore = create<AuthStore>()(
  persist(
    immer((set, get) => ({
      // Initial state - Hydrating while loading from localStorage
      authState: hydrating(),
      _hasHydrated: false,

      // Actions
      login: async (email: string, password: string): Promise<Result<LoginResponse, ApiError>> => {
        // Transition to Authenticating
        set((draft) => {
          draft.authState = authenticating(email)
        })

        // Call API
        const result = await apiLogin(email, password)

        if (isOk(result)) {
          const response = result.value
          // Calculate expiry (default 15 min if not provided)
          const expiresAt = new Date(Date.now() + 15 * 60 * 1000)

          // Transition to Authenticated
          set((draft) => {
            draft.authState = authenticated(
              response.access_token,
              response.user_id,
              response.email,
              response.role,
              expiresAt
            )
          })

          return result
        } else {
          // Determine error type
          const error = result.error.status === 401
            ? invalidCredentials('Invalid email or password')
            : result.error.status === 0
            ? networkError(result.error.message)
            : unknownAuthError(result.error.message)

          // Transition to AuthenticationFailed
          set((draft) => {
            draft.authState = authenticationFailed(email, error, new Date())
          })

          return result
        }
      },

      logout: () => {
        set((draft) => {
          draft.authState = unauthenticated()
        })
      },

      clearError: () => {
        const { authState } = get()
        if (authState.type === 'AuthenticationFailed') {
          set((draft) => {
            draft.authState = unauthenticated()
          })
        }
      },

      // Selectors
      isLoggedIn: () => {
        const state = get()
        return isAuthenticated(state.authState)
      },

      getToken: () => {
        const { authState } = get()
        return isAuthenticated(authState) ? authState.accessToken : null
      },

      getUserId: () => {
        const { authState } = get()
        return isAuthenticated(authState) ? authState.userId : null
      },

      getRole: () => {
        const { authState } = get()
        return isAuthenticated(authState) ? authState.role : null
      },

      hasHydrated: () => {
        return get()._hasHydrated
      },
    })),
    {
      name: 'healthhub-auth',

      // Persist full auth state including token for demo app
      // Note: In production, consider using httpOnly cookies or refresh tokens
      partialize: (state) => ({
        authState: state.authState,
      }),

      // Custom serialization for Date objects
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null
          return JSON.parse(str, (_key, value) => {
            if (value && typeof value === 'object' && value.__date) {
              return new Date(value.__date as string)
            }
            return value
          })
        },
        setItem: (name, value) => {
          const str = JSON.stringify(value, (_key, val) => {
            if (val instanceof Date) {
              return { __date: val.toISOString() }
            }
            return val
          })
          localStorage.setItem(name, str)
        },
        removeItem: (name) => localStorage.removeItem(name),
      },

      // Handle hydration complete
      onRehydrateStorage: () => {
        return (state, error) => {
          if (error) {
            console.error('[AuthStore] Hydration error:', error)
            if (state) {
              state.authState = unauthenticated()
              state._hasHydrated = true
            }
          } else if (state) {
            // If still Hydrating, no stored auth → Unauthenticated
            if (isHydrating(state.authState)) {
              state.authState = unauthenticated()
            }
            // Mark hydration complete
            state._hasHydrated = true
          }
        }
      },
    }
  )
)
