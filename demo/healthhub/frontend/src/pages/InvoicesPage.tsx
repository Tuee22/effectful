/**
 * InvoicesPage - Invoices list page.
 */

import { useInvoices } from '../hooks/useInvoices'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { InvoiceList } from '../components/invoices/InvoiceList'
import './InvoicesPage.css'

export const InvoicesPage = () => {
  const { invoiceList } = useInvoices()

  return (
    <div className="invoices-page" data-state={invoiceList.type}>
      <div className="page-header">
        <h1>Invoices</h1>
      </div>

      <RemoteDataRenderer
        data={invoiceList}
        notAsked={() => (
          <p className="page-empty">
            No invoices loaded. Refresh the page to load invoices.
          </p>
        )}
        success={(invoices) => <InvoiceList invoices={invoices} />}
      />
    </div>
  )
}
