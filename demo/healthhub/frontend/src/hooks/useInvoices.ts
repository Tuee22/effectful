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
  const fetchInvoices = useInvoiceStore((state) => state.fetchInvoices)
  const fetchInvoice = useInvoiceStore((state) => state.fetchInvoice)
  const clearCurrentInvoice = useInvoiceStore((state) => state.clearCurrentInvoice)

  const { token } = useAuth()

  // Auto-fetch invoices on mount when not yet loaded
  useEffect(() => {
    if (token && isNotAsked(invoiceList)) {
      fetchInvoices(token)
    }
  }, [token, invoiceList, fetchInvoices])

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
    fetchInvoices: () => {
      if (token) {
        fetchInvoices(token)
      }
    },
    fetchInvoice: (invoiceId: string) => {
      if (token) {
        fetchInvoice(invoiceId, token)
      }
    },
    clearCurrentInvoice,
  }
}
