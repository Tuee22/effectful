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
  const fetchLabResultsAction = useLabResultStore((state) => state.fetchLabResults)
  const fetchLabResultAction = useLabResultStore((state) => state.fetchLabResult)
  const clearCurrentLabResult = useLabResultStore((state) => state.clearCurrentLabResult)

  const { getValidAccessToken } = useAuth()

  // Auto-fetch lab results on mount when not yet loaded
  useEffect(() => {
    void (async () => {
      const token = await getValidAccessToken()
      if (token && isNotAsked(labResultList)) {
        await fetchLabResultsAction(token)
      }
    })()
  }, [labResultList, fetchLabResultsAction, getValidAccessToken])

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
    fetchLabResults: async () => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchLabResultsAction(token)
      }
    },
    fetchLabResult: async (labResultId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchLabResultAction(labResultId, token)
      }
    },
    clearCurrentLabResult,
  }
}
