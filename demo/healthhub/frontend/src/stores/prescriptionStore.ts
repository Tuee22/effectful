/**
 * Prescription Store using Zustand
 *
 * Manages prescription data with RemoteData for async states.
 */

import { create } from 'zustand'
import { RemoteData, notAsked, loading, success, failure } from '../algebraic/RemoteData'
import { Prescription } from '../models/Prescription'
import { ApiError } from '../api/client'
import { getPrescriptions, getPrescription, createPrescription, CreatePrescriptionRequest } from '../api/prescriptionApi'
import { isOk } from '../algebraic/Result'

export interface PrescriptionStore {
  // State
  currentPrescription: RemoteData<Prescription, ApiError>
  prescriptionList: RemoteData<Prescription[], ApiError>

  // Actions
  fetchPrescriptions: (token: string) => Promise<void>
  fetchPrescription: (prescriptionId: string, token: string) => Promise<void>
  createPrescription: (data: CreatePrescriptionRequest, token: string) => Promise<boolean>
  clearCurrentPrescription: () => void
}

export const usePrescriptionStore = create<PrescriptionStore>()((set, _get) => ({
  // Initial state
  currentPrescription: notAsked(),
  prescriptionList: notAsked(),

  // Actions
  fetchPrescriptions: async (token: string) => {
    // Set loading
    set({ prescriptionList: loading() })

    // Fetch from API
    const result = await getPrescriptions(token)

    // Update state based on result
    if (isOk(result)) {
      set({ prescriptionList: success(result.value) })
    } else {
      set({ prescriptionList: failure(result.error) })
    }
  },

  fetchPrescription: async (prescriptionId: string, token: string) => {
    // Set loading
    set({ currentPrescription: loading() })

    // Fetch from API
    const result = await getPrescription(prescriptionId, token)

    // Update state based on result
    if (isOk(result)) {
      set({ currentPrescription: success(result.value) })
    } else {
      set({ currentPrescription: failure(result.error) })
    }
  },

  createPrescription: async (data: CreatePrescriptionRequest, token: string): Promise<boolean> => {
    // Set loading
    set({ currentPrescription: loading() })

    // Create via API
    const result = await createPrescription(data, token)

    // Update state based on result
    if (isOk(result)) {
      set({ currentPrescription: success(result.value) })
    } else {
      set({ currentPrescription: failure(result.error) })
    }

    return isOk(result)
  },

  clearCurrentPrescription: () => {
    set({ currentPrescription: notAsked() })
  },
}))
