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
  const fetchPatients = usePatientStore((state) => state.fetchPatients)
  const fetchPatient = usePatientStore((state) => state.fetchPatient)
  const fetchPatientByUserId = usePatientStore((state) => state.fetchPatientByUserId)
  const createPatient = usePatientStore((state) => state.createPatient)
  const updatePatient = usePatientStore((state) => state.updatePatient)
  const clearCurrentPatient = usePatientStore((state) => state.clearCurrentPatient)

  const { token } = useAuth()

  // Auto-fetch patients on mount when not yet loaded
  useEffect(() => {
    if (token && isNotAsked(patientList)) {
      fetchPatients(token)
    }
  }, [token, patientList, fetchPatients])

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
    fetchPatients: () => {
      if (token) {
        fetchPatients(token)
      }
    },
    fetchPatient: (patientId: string) => {
      if (token) {
        fetchPatient(patientId, token)
      }
    },
    fetchPatientByUserId: (userId: string) => {
      if (token) {
        fetchPatientByUserId(userId, token)
      }
    },
    createPatient: (data: Parameters<typeof createPatient>[0]) => {
      if (token) {
        return createPatient(data, token)
      }
      return Promise.resolve(false)
    },
    updatePatient: (patientId: string, data: Parameters<typeof updatePatient>[1]) => {
      if (token) {
        return updatePatient(patientId, data, token)
      }
      return Promise.resolve(false)
    },
    clearCurrentPatient,
  }
}

// Hook that fetches patient by user ID on mount
export const useCurrentPatient = () => {
  const { userId, token, isAuthenticated } = useAuth()
  const { currentPatient } = usePatients()

  useEffect(() => {
    if (isAuthenticated && userId && token) {
      const fetchPatient = usePatientStore.getState().fetchPatientByUserId
      fetchPatient(userId, token)
    }
  }, [isAuthenticated, userId, token])

  return currentPatient
}
