/**
 * Invoice domain model.
 */

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue'

export interface LineItem {
  readonly id: string
  readonly invoiceId: string
  readonly description: string
  readonly quantity: number
  readonly unitPrice: number
  readonly total: number
  readonly createdAt: Date
}

export interface Invoice {
  readonly id: string
  readonly patientId: string
  readonly appointmentId: string | null
  readonly status: InvoiceStatus
  readonly subtotal: number
  readonly taxAmount: number
  readonly totalAmount: number
  readonly dueDate: Date | null
  readonly paidAt: Date | null
  readonly createdAt: Date
  readonly updatedAt: Date
}

export interface InvoiceWithLineItems {
  readonly invoice: Invoice
  readonly lineItems: readonly LineItem[]
}

// API response types
export interface LineItemApiResponse {
  readonly id: string
  readonly invoice_id: string
  readonly description: string
  readonly quantity: number
  readonly unit_price: number
  readonly total: number
  readonly created_at: string
}

export interface InvoiceApiResponse {
  readonly id: string
  readonly patient_id: string
  readonly appointment_id: string | null
  readonly status: InvoiceStatus
  readonly subtotal: number
  readonly tax_amount: number
  readonly total_amount: number
  readonly due_date: string | null
  readonly paid_at: string | null
  readonly created_at: string
  readonly updated_at: string
}

export interface InvoiceWithLineItemsApiResponse {
  readonly invoice: InvoiceApiResponse
  readonly line_items: LineItemApiResponse[]
}

// Converters
export const lineItemFromApiResponse = (response: LineItemApiResponse): LineItem => ({
  id: response.id,
  invoiceId: response.invoice_id,
  description: response.description,
  quantity: response.quantity,
  unitPrice: response.unit_price,
  total: response.total,
  createdAt: new Date(response.created_at),
})

export const fromApiResponse = (response: InvoiceApiResponse): Invoice => ({
  id: response.id,
  patientId: response.patient_id,
  appointmentId: response.appointment_id,
  status: response.status,
  subtotal: response.subtotal,
  taxAmount: response.tax_amount,
  totalAmount: response.total_amount,
  dueDate: response.due_date ? new Date(response.due_date) : null,
  paidAt: response.paid_at ? new Date(response.paid_at) : null,
  createdAt: new Date(response.created_at),
  updatedAt: new Date(response.updated_at),
})

export const invoiceWithLineItemsFromApiResponse = (response: InvoiceWithLineItemsApiResponse): InvoiceWithLineItems => ({
  invoice: fromApiResponse(response.invoice),
  lineItems: response.line_items.map(lineItemFromApiResponse),
})

// Display helpers
export const getStatusLabel = (status: InvoiceStatus): string => {
  switch (status) {
    case 'draft':
      return 'Draft'
    case 'sent':
      return 'Sent'
    case 'paid':
      return 'Paid'
    case 'overdue':
      return 'Overdue'
  }
}

export const getStatusColor = (status: InvoiceStatus): string => {
  switch (status) {
    case 'draft':
      return '#6b7280' // Gray
    case 'sent':
      return '#3b82f6' // Blue
    case 'paid':
      return '#10b981' // Green
    case 'overdue':
      return '#ef4444' // Red
  }
}

export const formatCurrency = (amount: number): string =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)

export const formatDate = (date: Date): string =>
  date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
