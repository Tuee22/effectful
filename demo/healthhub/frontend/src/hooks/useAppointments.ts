/**
 * useAppointments hook - Convenience wrapper for appointment store.
 */

import { useAppointmentStore } from '../stores/appointmentStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure } from '../algebraic/RemoteData'

export const useAppointments = () => {
  const currentAppointment = useAppointmentStore((state) => state.currentAppointment)
  const appointmentList = useAppointmentStore((state) => state.appointmentList)
  const fetchAppointmentAction = useAppointmentStore((state) => state.fetchAppointment)
  const createAppointmentAction = useAppointmentStore((state) => state.createAppointment)
  const transitionStatusAction = useAppointmentStore((state) => state.transitionStatus)
  const clearCurrentAppointment = useAppointmentStore((state) => state.clearCurrentAppointment)

  const { userId, getValidAccessToken } = useAuth()

  return {
    // State
    currentAppointment,
    appointmentList,

    // Computed
    appointment: isSuccess(currentAppointment) ? currentAppointment.data : null,
    appointments: isSuccess(appointmentList) ? appointmentList.data : [],
    isLoading: isLoading(currentAppointment),
    error: isFailure(currentAppointment) ? currentAppointment.error : null,

    // Actions (with token injection)
    fetchAppointment: async (appointmentId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchAppointmentAction(appointmentId, token)
      }
    },
    createAppointment: async (data: Parameters<typeof createAppointmentAction>[0]) => {
      const token = await getValidAccessToken()
      if (!token) {
        return false
      }
      return createAppointmentAction(data, token)
    },
    transitionStatus: async (appointmentId: string, newStatus: string) => {
      const token = await getValidAccessToken()
      if (token && userId) {
        return transitionStatusAction(appointmentId, newStatus, userId, token)
      }
      return Promise.resolve(false)
    },
    clearCurrentAppointment,
  }
}
