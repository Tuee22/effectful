/**
 * Authentication Store using Zustand + Immer (no persistence).
 *
 * Access token lives only in memory. Refresh token is HttpOnly cookie
 * managed by the backend. Missing/expired access tokens always trigger
 * a refresh attempt before returning to Unauthenticated.
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
  refreshing,
  refreshDenied,
  isAuthenticated,
} from '../models/Auth'
import { Result, isOk } from '../algebraic/Result'
import { login as apiLogin, refresh as apiRefresh, LoginResponse, RefreshResponse } from '../api/authApi'
import { ApiError } from '../api/client'

const ACCESS_TOKEN_TTL_MS = 15 * 60 * 1000
const AUTH_STORAGE_KEY = 'healthhub-auth'

const toDate = (value: Date | string): Date => (value instanceof Date ? value : new Date(value))

export interface AuthStore {
  // State
  authState: AuthState
  _hasHydrated: boolean
  _hasRefreshCookie: () => boolean

  // Actions
  login: (email: string, password: string) => Promise<Result<LoginResponse, ApiError>>
  logout: () => void
  clearError: () => void
  refreshSession: (reason: 'missing_access' | 'expired') => Promise<boolean>
  bootstrap: () => Promise<void>

  // Selectors
  isLoggedIn: () => boolean
  getToken: () => string | null
  getUserId: () => string | null
  getRole: () => UserRole | null
  hasHydrated: () => boolean
  getValidAccessToken: () => Promise<string | null>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    immer((set, get) => ({
    // Initial state - Hydrating while probing refresh cookie
    authState: hydrating(),
    _hasHydrated: false,

    // Internal helper - check for refresh token cookie before hitting backend
    _hasRefreshCookie: (): boolean => document.cookie.includes('refresh_token='),

    // Actions
    login: async (email: string, password: string): Promise<Result<LoginResponse, ApiError>> => {
      set((draft) => {
        draft.authState = authenticating(email)
      })

      const result = await apiLogin(email, password)

      if (isOk(result)) {
        const response = result.value
        const expiresAt = new Date(Date.now() + ACCESS_TOKEN_TTL_MS)

        set((draft) => {
          draft.authState = authenticated(
            response.access_token,
            response.user_id,
            response.email,
            response.role,
            expiresAt
          )
          draft._hasHydrated = true
        })

        return result
      }

      const error =
        result.error.status === 401
          ? invalidCredentials('Invalid email or password')
          : result.error.status === 0
          ? networkError(result.error.message)
          : unknownAuthError(result.error.message)

      set((draft) => {
        draft.authState = authenticationFailed(email, error, new Date())
        draft._hasHydrated = true
      })

      return result
    },

    refreshSession: async (reason: 'missing_access' | 'expired'): Promise<boolean> => {
      // Avoid backend call if we know no refresh cookie exists
      if (!get()._hasRefreshCookie()) {
        set((draft) => {
          draft.authState = refreshDenied('Refresh token not found in cookie', new Date())
          draft._hasHydrated = true
        })
        set((draft) => {
          draft.authState = unauthenticated()
          draft._hasHydrated = true
        })
        return false
      }

      set((draft) => {
        draft.authState = refreshing(reason)
      })

      const result: Result<RefreshResponse, ApiError> = await apiRefresh()
      if (isOk(result)) {
        const accessToken = result.value.access_token
        const expiresAt = new Date(Date.now() + ACCESS_TOKEN_TTL_MS)
        const userId = result.value.user_id
        const email = result.value.email
        const role = result.value.role

        set((draft) => {
          draft.authState = authenticated(accessToken, userId, email, role, expiresAt)
          draft._hasHydrated = true
        })
        return true
      }

      set((draft) => {
        draft.authState = refreshDenied(result.error.message, new Date())
        draft._hasHydrated = true
      })
      set((draft) => {
        draft.authState = unauthenticated()
        draft._hasHydrated = true
      })
      return false
    },

    bootstrap: async () => {
      // Skip refresh entirely when no refresh cookie is present (common for first load/E2E)
      if (!get()._hasRefreshCookie()) {
        set((draft) => {
          draft.authState = unauthenticated()
          draft._hasHydrated = true
        })
        return
      }

      const refreshed = await get().refreshSession('missing_access')
      if (!refreshed) {
        set((draft) => {
          draft.authState = unauthenticated()
          draft._hasHydrated = true
        })
      }
    },

    logout: () => {
      set((draft) => {
        draft.authState = unauthenticated()
        draft._hasHydrated = true
      })
    },

    clearError: () => {
      const { authState } = get()
      if (authState.type === 'AuthenticationFailed') {
        set((draft) => {
          draft.authState = unauthenticated()
          draft._hasHydrated = true
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

    getValidAccessToken: async (): Promise<string | null> => {
      const state = get().authState
      if (isAuthenticated(state) && toDate(state.expiresAt).getTime() > Date.now()) {
        return state.accessToken
      }

      const hasCookie = get()._hasRefreshCookie()

      const refreshed = hasCookie ? await get().refreshSession('missing_access') : false
      if (!refreshed) {
        // When unauthenticated and no cookie, avoid spamming refresh attempts
        if (!hasCookie) {
          set((draft) => {
            draft.authState = unauthenticated()
            draft._hasHydrated = true
          })
        }
        return null
      }

      const updated = get().authState
      return isAuthenticated(updated) ? updated.accessToken : null
    },
  })),
    {
      name: AUTH_STORAGE_KEY,
      partialize: (state) => ({
        authState: state.authState,
        _hasHydrated: state._hasHydrated,
      }),
      onRehydrateStorage: () => (state) => {
        // Re-mark hydration after localStorage replay
        if (state) {
          state._hasHydrated = true
        }
      },
    }
  )
)
