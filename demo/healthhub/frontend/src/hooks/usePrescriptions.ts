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
  const fetchPrescriptionsAction = usePrescriptionStore((state) => state.fetchPrescriptions)
  const fetchPrescriptionAction = usePrescriptionStore((state) => state.fetchPrescription)
  const createPrescriptionAction = usePrescriptionStore((state) => state.createPrescription)
  const clearCurrentPrescription = usePrescriptionStore((state) => state.clearCurrentPrescription)

  const { getValidAccessToken } = useAuth()

  // Auto-fetch prescriptions on mount when not yet loaded
  useEffect(() => {
    void (async () => {
      const token = await getValidAccessToken()
      if (token && isNotAsked(prescriptionList)) {
        await fetchPrescriptionsAction(token)
      }
    })()
  }, [prescriptionList, fetchPrescriptionsAction, getValidAccessToken])

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
    fetchPrescriptions: async () => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchPrescriptionsAction(token)
      }
    },
    fetchPrescription: async (prescriptionId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchPrescriptionAction(prescriptionId, token)
      }
    },
    createPrescription: async (data: Parameters<typeof createPrescriptionAction>[0]) => {
      const token = await getValidAccessToken()
      if (!token) {
        return false
      }
      return createPrescriptionAction(data, token)
    },
    clearCurrentPrescription,
  }
}
