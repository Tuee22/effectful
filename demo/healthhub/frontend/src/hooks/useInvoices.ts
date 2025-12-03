/**
 * useInvoices hook - Convenience wrapper for invoice store.
 */

import { useEffect } from 'react'
import { useInvoiceStore } from '../stores/invoiceStore'
import { useAuth } from './useAuth'
import { isSuccess, isLoading, isFailure, isNotAsked } from '../algebraic/RemoteData'

export const useInvoices = () => {
  const currentInvoice = useInvoiceStore((state) => state.currentInvoice)
  const invoiceList = useInvoiceStore((state) => state.invoiceList)
  const fetchInvoicesAction = useInvoiceStore((state) => state.fetchInvoices)
  const fetchInvoiceAction = useInvoiceStore((state) => state.fetchInvoice)
  const clearCurrentInvoice = useInvoiceStore((state) => state.clearCurrentInvoice)

  const { getValidAccessToken } = useAuth()

  // Auto-fetch invoices on mount when not yet loaded
  useEffect(() => {
    void (async () => {
      const token = await getValidAccessToken()
      if (token && isNotAsked(invoiceList)) {
        await fetchInvoicesAction(token)
      }
    })()
  }, [invoiceList, fetchInvoicesAction, getValidAccessToken])

  return {
    // State
    currentInvoice,
    invoiceList,

    // Computed
    invoice: isSuccess(currentInvoice) ? currentInvoice.data : null,
    invoices: isSuccess(invoiceList) ? invoiceList.data : [],
    isLoading: isLoading(currentInvoice) || isLoading(invoiceList),
    error: isFailure(currentInvoice) ? currentInvoice.error : null,
    listError: isFailure(invoiceList) ? invoiceList.error : null,

    // Actions (with token injection)
    fetchInvoices: async () => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchInvoicesAction(token)
      }
    },
    fetchInvoice: async (invoiceId: string) => {
      const token = await getValidAccessToken()
      if (token) {
        await fetchInvoiceAction(invoiceId, token)
      }
    },
    clearCurrentInvoice,
  }
}
