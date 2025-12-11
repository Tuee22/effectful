/**
 * useAppointments hook - Convenience wrapper for appointment store.
 */

import { useEffect } from 'react'
import { useAppointmentStore } from '../stores/appointmentStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure, isNotAsked } from '../algebraic/RemoteData'

export const useAppointments = () => {
  const currentAppointment = useAppointmentStore((state) => state.currentAppointment)
  const appointmentList = useAppointmentStore((state) => state.appointmentList)
  const fetchAppointmentsAction = useAppointmentStore((state) => state.fetchAppointments)
  const fetchAppointmentAction = useAppointmentStore((state) => state.fetchAppointment)
  const createAppointmentAction = useAppointmentStore((state) => state.createAppointment)
  const transitionStatusAction = useAppointmentStore((state) => state.transitionStatus)
  const clearCurrentAppointment = useAppointmentStore((state) => state.clearCurrentAppointment)

  const { userId, getValidAccessToken } = useAuth()

  useEffect(() => {
    void (async () => {
      const token = await getValidAccessToken()
      if (token && isNotAsked(appointmentList)) {
        await fetchAppointmentsAction(token)
      }
    })()
  }, [appointmentList, fetchAppointmentsAction, getValidAccessToken])

  return {
    // State
    currentAppointment,
    appointmentList,

    // Computed
    appointment: isSuccess(currentAppointment) ? currentAppointment.data : null,
    appointments: isSuccess(appointmentList) ? appointmentList.data : [],
    isLoading: isLoading(currentAppointment) || isLoading(appointmentList),
    error: isFailure(currentAppointment) ? currentAppointment.error : null,

    // Actions (with token injection)
    fetchAppointment: async (appointmentId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchAppointmentAction(appointmentId, token)
      }
    },
    fetchAppointments: async (statusFilter?: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchAppointmentsAction(token, statusFilter)
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
