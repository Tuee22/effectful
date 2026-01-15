/**
 * Lab Result Store using Zustand
 */

import { create } from 'zustand'
import { RemoteData, notAsked, loading, success, failure } from '../algebraic/RemoteData'
import { LabResult } from '../models/LabResult'
import { ApiError } from '../api/client'
import { getLabResults, getLabResult } from '../api/labResultApi'
import { isOk } from '../algebraic/Result'

export interface LabResultStore {
  currentLabResult: RemoteData<LabResult, ApiError>
  labResultList: RemoteData<LabResult[], ApiError>

  fetchLabResults: (token: string) => Promise<void>
  fetchLabResult: (labResultId: string, token: string) => Promise<void>
  clearCurrentLabResult: () => void
}

export const useLabResultStore = create<LabResultStore>()((set) => ({
  currentLabResult: notAsked(),
  labResultList: notAsked(),

  fetchLabResults: async (token: string) => {
    set({ labResultList: loading() })
    const result = await getLabResults(token)
    if (isOk(result)) {
      set({ labResultList: success(result.value) })
    } else {
      set({ labResultList: failure(result.error) })
    }
  },

  fetchLabResult: async (labResultId: string, token: string) => {
    set({ currentLabResult: loading() })
    const result = await getLabResult(labResultId, token)
    if (isOk(result)) {
      set({ currentLabResult: success(result.value) })
    } else {
      set({ currentLabResult: failure(result.error) })
    }
  },

  clearCurrentLabResult: () => {
    set({ currentLabResult: notAsked() })
  },
}))
