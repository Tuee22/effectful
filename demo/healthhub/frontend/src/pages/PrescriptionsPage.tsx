/**
 * PrescriptionsPage - Prescriptions list page.
 */

import { usePrescriptions } from '../hooks/usePrescriptions'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { PrescriptionList } from '../components/prescriptions/PrescriptionList'
import './PrescriptionsPage.css'

export const PrescriptionsPage = () => {
  const { prescriptionList } = usePrescriptions()

  return (
    <div className="prescriptions-page">
      <div className="page-header">
        <h1>Prescriptions</h1>
      </div>

      <RemoteDataRenderer
        data={prescriptionList}
        notAsked={() => (
          <p className="page-empty">
            No prescriptions loaded. Refresh the page to load prescriptions.
          </p>
        )}
        success={(prescriptions) => <PrescriptionList prescriptions={prescriptions} />}
      />
    </div>
  )
}
