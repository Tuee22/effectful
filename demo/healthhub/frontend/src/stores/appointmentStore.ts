/**
 * Appointment Store using Zustand + Immer
 *
 * Manages appointment data with RemoteData for async states.
 */

import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import { RemoteData, notAsked, loading, success, failure } from '../algebraic/RemoteData'
import { Appointment } from '../models/Appointment'
import { ApiError } from '../api/client'
import {
  getAppointments,
  getAppointment,
  createAppointment,
  transitionAppointmentStatus,
  CreateAppointmentRequest,
} from '../api/appointmentApi'
import { isOk } from '../algebraic/Result'

export interface AppointmentStore {
  // State
  currentAppointment: RemoteData<Appointment, ApiError>
  appointmentList: RemoteData<Appointment[], ApiError>

  // Actions
  fetchAppointments: (token: string, statusFilter?: string) => Promise<void>
  fetchAppointment: (appointmentId: string, token: string) => Promise<void>
  createAppointment: (data: CreateAppointmentRequest, token: string) => Promise<boolean>
  transitionStatus: (
    appointmentId: string,
    newStatus: string,
    actorId: string,
    token: string
  ) => Promise<boolean>
  clearCurrentAppointment: () => void
}

export const useAppointmentStore = create<AppointmentStore>()(
  immer((set, _get) => ({
    // Initial state
    currentAppointment: notAsked(),
    appointmentList: notAsked(),

    // Actions
    fetchAppointments: async (token: string, statusFilter?: string) => {
      set((draft) => {
        draft.appointmentList = loading()
      })

      const result = await getAppointments(token, statusFilter)

      set((draft) => {
        if (isOk(result)) {
          draft.appointmentList = success(result.value)
        } else {
          draft.appointmentList = failure(result.error)
        }
      })
    },

    fetchAppointment: async (appointmentId: string, token: string) => {
      // Set loading
      set((draft) => {
        draft.currentAppointment = loading()
      })

      // Fetch from API
      const result = await getAppointment(appointmentId, token)

      // Update state based on result
      set((draft) => {
        if (isOk(result)) {
          draft.currentAppointment = success(result.value)
        } else {
          draft.currentAppointment = failure(result.error)
        }
      })
    },

    createAppointment: async (
      data: CreateAppointmentRequest,
      token: string
    ): Promise<boolean> => {
      // Set loading
      set((draft) => {
        draft.currentAppointment = loading()
      })

      // Create via API
      const result = await createAppointment(data, token)

      // Update state based on result
      set((draft) => {
        if (isOk(result)) {
          draft.currentAppointment = success(result.value)
        } else {
          draft.currentAppointment = failure(result.error)
        }
      })

      if (isOk(result)) {
        const listResult = await getAppointments(token)
        set((draft) => {
          if (isOk(listResult)) {
            draft.appointmentList = success(listResult.value)
          }
        })
      }

      return isOk(result)
    },

    transitionStatus: async (
      appointmentId: string,
      newStatus: string,
      actorId: string,
      token: string
    ): Promise<boolean> => {
      // Call API
      const result = await transitionAppointmentStatus(
        appointmentId,
        newStatus,
        actorId,
        token
      )

      if (isOk(result)) {
        // Refetch to get updated appointment
        const fetchResult = await getAppointment(appointmentId, token)
        set((draft) => {
          if (isOk(fetchResult)) {
            draft.currentAppointment = success(fetchResult.value)
          }
        })
        return true
      }

      return false
    },

    clearCurrentAppointment: () => {
      set((draft) => {
        draft.currentAppointment = notAsked()
      })
    },
  }))
)
