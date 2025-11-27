/**
 * Patient Store using Zustand
 *
 * Manages patient data with RemoteData for async states.
 * Uses standard Zustand set (no immer) to avoid readonly/mutable conflicts.
 */

import { create } from 'zustand'
import { RemoteData, notAsked, loading, success, failure } from '../algebraic/RemoteData'
import { Patient } from '../models/Patient'
import { ApiError } from '../api/client'
import { getPatients, getPatient, getPatientByUserId, createPatient, updatePatient, CreatePatientRequest, UpdatePatientRequest } from '../api/patientApi'
import { isOk } from '../algebraic/Result'

export interface PatientStore {
  // State
  currentPatient: RemoteData<Patient, ApiError>
  patientList: RemoteData<Patient[], ApiError>
  patientsByUserId: Map<string, RemoteData<Patient, ApiError>>

  // Actions
  fetchPatients: (token: string) => Promise<void>
  fetchPatient: (patientId: string, token: string) => Promise<void>
  fetchPatientByUserId: (userId: string, token: string) => Promise<void>
  createPatient: (data: CreatePatientRequest, token: string) => Promise<boolean>
  updatePatient: (patientId: string, data: UpdatePatientRequest, token: string) => Promise<boolean>
  clearCurrentPatient: () => void
}

export const usePatientStore = create<PatientStore>()((set, _get) => ({
  // Initial state
  currentPatient: notAsked(),
  patientList: notAsked(),
  patientsByUserId: new Map(),

  // Actions
  fetchPatients: async (token: string) => {
    // Set loading
    set({ patientList: loading() })

    // Fetch from API
    const result = await getPatients(token)

    // Update state based on result
    if (isOk(result)) {
      set({ patientList: success(result.value) })
    } else {
      set({ patientList: failure(result.error) })
    }
  },

  fetchPatient: async (patientId: string, token: string) => {
    // Set loading
    set({ currentPatient: loading() })

    // Fetch from API
    const result = await getPatient(patientId, token)

    // Update state based on result
    if (isOk(result)) {
      set({ currentPatient: success(result.value) })
    } else {
      set({ currentPatient: failure(result.error) })
    }
  },

  fetchPatientByUserId: async (userId: string, token: string) => {
    // Set loading
    set((state) => ({
      currentPatient: loading(),
      patientsByUserId: new Map(state.patientsByUserId).set(userId, loading()),
    }))

    // Fetch from API
    const result = await getPatientByUserId(userId, token)

    // Update state based on result
    if (isOk(result)) {
      const patient = result.value
      set((state) => ({
        currentPatient: success(patient),
        patientsByUserId: new Map(state.patientsByUserId).set(userId, success(patient)),
      }))
    } else {
      set((state) => ({
        currentPatient: failure(result.error),
        patientsByUserId: new Map(state.patientsByUserId).set(userId, failure(result.error)),
      }))
    }
  },

  createPatient: async (data: CreatePatientRequest, token: string): Promise<boolean> => {
    // Set loading
    set({ currentPatient: loading() })

    // Create via API
    const result = await createPatient(data, token)

    // Update state based on result
    if (isOk(result)) {
      set({ currentPatient: success(result.value) })
    } else {
      set({ currentPatient: failure(result.error) })
    }

    return isOk(result)
  },

  updatePatient: async (patientId: string, data: UpdatePatientRequest, token: string): Promise<boolean> => {
    // Set loading
    set({ currentPatient: loading() })

    // Update via API
    const result = await updatePatient(patientId, data, token)

    // Update state based on result
    if (isOk(result)) {
      set({ currentPatient: success(result.value) })
    } else {
      set({ currentPatient: failure(result.error) })
    }

    return isOk(result)
  },

  clearCurrentPatient: () => {
    set({ currentPatient: notAsked() })
  },
}))
