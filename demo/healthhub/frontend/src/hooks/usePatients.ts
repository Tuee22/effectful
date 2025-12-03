/**
 * usePatients hook - Convenience wrapper for patient store.
 */

import { useEffect } from 'react'
import { usePatientStore } from '../stores/patientStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure, isNotAsked } from '../algebraic/RemoteData'

export const usePatients = () => {
  const currentPatient = usePatientStore((state) => state.currentPatient)
  const patientList = usePatientStore((state) => state.patientList)
  const fetchPatientsAction = usePatientStore((state) => state.fetchPatients)
  const fetchPatientAction = usePatientStore((state) => state.fetchPatient)
  const fetchPatientByUserIdAction = usePatientStore((state) => state.fetchPatientByUserId)
  const createPatientAction = usePatientStore((state) => state.createPatient)
  const updatePatientAction = usePatientStore((state) => state.updatePatient)
  const clearCurrentPatient = usePatientStore((state) => state.clearCurrentPatient)

  const { getValidAccessToken } = useAuth()

  // Auto-fetch patients on mount when not yet loaded
  useEffect(() => {
    void (async () => {
      const token = await getValidAccessToken()
      if (token && isNotAsked(patientList)) {
        await fetchPatientsAction(token)
      }
    })()
  }, [patientList, fetchPatientsAction, getValidAccessToken])

  return {
    // State
    currentPatient,
    patientList,

    // Computed
    patient: isSuccess(currentPatient) ? currentPatient.data : null,
    patients: isSuccess(patientList) ? patientList.data : [],
    isLoading: isLoading(currentPatient) || isLoading(patientList),
    error: isFailure(currentPatient) ? currentPatient.error : null,
    listError: isFailure(patientList) ? patientList.error : null,

    // Actions (with token injection)
    fetchPatients: async () => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchPatientsAction(token)
      }
    },
    fetchPatient: async (patientId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchPatientAction(patientId, token)
      }
    },
    fetchPatientByUserId: async (userId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchPatientByUserIdAction(userId, token)
      }
    },
    createPatient: async (data: Parameters<typeof createPatientAction>[0]) => {
      const token = await getValidAccessToken()
      if (!token) {
        return false
      }
      return createPatientAction(data, token)
    },
    updatePatient: async (patientId: string, data: Parameters<typeof updatePatientAction>[1]) => {
      const token = await getValidAccessToken()
      if (!token) {
        return false
      }
      return updatePatientAction(patientId, data, token)
    },
    clearCurrentPatient,
  }
}

// Hook that fetches patient by user ID on mount
export const useCurrentPatient = () => {
  const { userId, isAuthenticated, getValidAccessToken } = useAuth()
  const { currentPatient } = usePatients()

  useEffect(() => {
    void (async () => {
      if (isAuthenticated && userId) {
        const token = await getValidAccessToken()
        if (token) {
          const fetchPatient = usePatientStore.getState().fetchPatientByUserId
          fetchPatient(userId, token)
        }
      }
    })()
  }, [isAuthenticated, userId, getValidAccessToken])

  return currentPatient
}
