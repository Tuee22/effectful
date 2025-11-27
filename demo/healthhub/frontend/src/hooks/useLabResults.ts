/**
 * useLabResults hook - Convenience wrapper for lab result store.
 */

import { useEffect } from 'react'
import { useLabResultStore } from '../stores/labResultStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure, isNotAsked } from '../algebraic/RemoteData'

export const useLabResults = () => {
  const currentLabResult = useLabResultStore((state) => state.currentLabResult)
  const labResultList = useLabResultStore((state) => state.labResultList)
  const fetchLabResults = useLabResultStore((state) => state.fetchLabResults)
  const fetchLabResult = useLabResultStore((state) => state.fetchLabResult)
  const clearCurrentLabResult = useLabResultStore((state) => state.clearCurrentLabResult)

  const { token } = useAuth()

  // Auto-fetch lab results on mount when not yet loaded
  useEffect(() => {
    if (token && isNotAsked(labResultList)) {
      fetchLabResults(token)
    }
  }, [token, labResultList, fetchLabResults])

  return {
    // State
    currentLabResult,
    labResultList,

    // Computed
    labResult: isSuccess(currentLabResult) ? currentLabResult.data : null,
    labResults: isSuccess(labResultList) ? labResultList.data : [],
    isLoading: isLoading(currentLabResult) || isLoading(labResultList),
    error: isFailure(currentLabResult) ? currentLabResult.error : null,
    listError: isFailure(labResultList) ? labResultList.error : null,

    // Actions (with token injection)
    fetchLabResults: () => {
      if (token) {
        fetchLabResults(token)
      }
    },
    fetchLabResult: (labResultId: string) => {
      if (token) {
        fetchLabResult(labResultId, token)
      }
    },
    clearCurrentLabResult,
  }
}
