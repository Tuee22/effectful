/**
 * InvoiceList component - List of invoices.
 */

import { Link } from 'react-router-dom'
import { Invoice, invoiceGetStatusLabel, invoiceGetStatusColor, invoiceFormatCurrency, invoiceFormatDate } from '../../models'
import './InvoiceList.css'

interface InvoiceListProps {
  readonly invoices: readonly Invoice[]
}

interface StatusBadgeProps {
  readonly invoice: Invoice
}

const StatusBadge = ({ invoice }: StatusBadgeProps) => {
  return (
    <span
      className="invoice-status-badge"
      style={{ backgroundColor: invoiceGetStatusColor(invoice.status) }}
    >
      {invoiceGetStatusLabel(invoice.status)}
    </span>
  )
}

export const InvoiceList = ({ invoices }: InvoiceListProps) => {
  if (invoices.length === 0) {
    return (
      <div className="invoice-list-empty">
        <p>No invoices found.</p>
      </div>
    )
  }

  return (
    <div className="invoice-list">
      <table className="invoice-table">
        <thead>
          <tr>
            <th>Invoice #</th>
            <th>Date</th>
            <th>Due Date</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id}>
              <td className="invoice-number">{invoice.id.substring(0, 8).toUpperCase()}</td>
              <td>{invoiceFormatDate(invoice.createdAt)}</td>
              <td>{invoice.dueDate ? invoiceFormatDate(invoice.dueDate) : '-'}</td>
              <td className="invoice-amount">{invoiceFormatCurrency(invoice.totalAmount)}</td>
              <td>
                <StatusBadge invoice={invoice} />
              </td>
              <td>
                <Link
                  to={`/invoices/${invoice.id}`}
                  className="invoice-view-link"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
