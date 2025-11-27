/**
 * usePrescriptions hook - Convenience wrapper for prescription store.
 */

import { useEffect } from 'react'
import { usePrescriptionStore } from '../stores/prescriptionStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure, isNotAsked } from '../algebraic/RemoteData'

export const usePrescriptions = () => {
  const currentPrescription = usePrescriptionStore((state) => state.currentPrescription)
  const prescriptionList = usePrescriptionStore((state) => state.prescriptionList)
  const fetchPrescriptions = usePrescriptionStore((state) => state.fetchPrescriptions)
  const fetchPrescription = usePrescriptionStore((state) => state.fetchPrescription)
  const createPrescription = usePrescriptionStore((state) => state.createPrescription)
  const clearCurrentPrescription = usePrescriptionStore((state) => state.clearCurrentPrescription)

  const { token } = useAuth()

  // Auto-fetch prescriptions on mount when not yet loaded
  useEffect(() => {
    if (token && isNotAsked(prescriptionList)) {
      fetchPrescriptions(token)
    }
  }, [token, prescriptionList, fetchPrescriptions])

  return {
    // State
    currentPrescription,
    prescriptionList,

    // Computed
    prescription: isSuccess(currentPrescription) ? currentPrescription.data : null,
    prescriptions: isSuccess(prescriptionList) ? prescriptionList.data : [],
    isLoading: isLoading(currentPrescription) || isLoading(prescriptionList),
    error: isFailure(currentPrescription) ? currentPrescription.error : null,
    listError: isFailure(prescriptionList) ? prescriptionList.error : null,

    // Actions (with token injection)
    fetchPrescriptions: () => {
      if (token) {
        fetchPrescriptions(token)
      }
    },
    fetchPrescription: (prescriptionId: string) => {
      if (token) {
        fetchPrescription(prescriptionId, token)
      }
    },
    createPrescription: (data: Parameters<typeof createPrescription>[0]) => {
      if (token) {
        return createPrescription(data, token)
      }
      return Promise.resolve(false)
    },
    clearCurrentPrescription,
  }
}
