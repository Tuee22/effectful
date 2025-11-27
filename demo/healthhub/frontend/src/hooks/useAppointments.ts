/**
 * useAppointments hook - Convenience wrapper for appointment store.
 */

import { useAppointmentStore } from '../stores/appointmentStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure } from '../algebraic/RemoteData'

export const useAppointments = () => {
  const currentAppointment = useAppointmentStore((state) => state.currentAppointment)
  const appointmentList = useAppointmentStore((state) => state.appointmentList)
  const fetchAppointment = useAppointmentStore((state) => state.fetchAppointment)
  const createAppointment = useAppointmentStore((state) => state.createAppointment)
  const transitionStatus = useAppointmentStore((state) => state.transitionStatus)
  const clearCurrentAppointment = useAppointmentStore((state) => state.clearCurrentAppointment)

  const { token, userId } = useAuth()

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
    fetchAppointment: (appointmentId: string) => {
      if (token) {
        fetchAppointment(appointmentId, token)
      }
    },
    createAppointment: (data: Parameters<typeof createAppointment>[0]) => {
      if (token) {
        return createAppointment(data, token)
      }
      return Promise.resolve(false)
    },
    transitionStatus: (appointmentId: string, newStatus: string) => {
      if (token && userId) {
        return transitionStatus(appointmentId, newStatus, userId, token)
      }
      return Promise.resolve(false)
    },
    clearCurrentAppointment,
  }
}
