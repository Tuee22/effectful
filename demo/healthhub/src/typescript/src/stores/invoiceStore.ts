/**
 * Invoice Store using Zustand
 */

import { create } from 'zustand'
import { RemoteData, notAsked, loading, success, failure } from '../algebraic/RemoteData'
import { Invoice, InvoiceWithLineItems } from '../models/Invoice'
import { ApiError } from '../api/client'
import { getInvoices, getInvoice } from '../api/invoiceApi'
import { isOk } from '../algebraic/Result'

export interface InvoiceStore {
  currentInvoice: RemoteData<InvoiceWithLineItems, ApiError>
  invoiceList: RemoteData<Invoice[], ApiError>

  fetchInvoices: (token: string) => Promise<void>
  fetchInvoice: (invoiceId: string, token: string) => Promise<void>
  clearCurrentInvoice: () => void
}

export const useInvoiceStore = create<InvoiceStore>()((set) => ({
  currentInvoice: notAsked(),
  invoiceList: notAsked(),

  fetchInvoices: async (token: string) => {
    set({ invoiceList: loading() })
    const result = await getInvoices(token)
    if (isOk(result)) {
      set({ invoiceList: success(result.value) })
    } else {
      set({ invoiceList: failure(result.error) })
    }
  },

  fetchInvoice: async (invoiceId: string, token: string) => {
    set({ currentInvoice: loading() })
    const result = await getInvoice(invoiceId, token)
    if (isOk(result)) {
      set({ currentInvoice: success(result.value) })
    } else {
      set({ currentInvoice: failure(result.error) })
    }
  },

  clearCurrentInvoice: () => {
    set({ currentInvoice: notAsked() })
  },
}))
