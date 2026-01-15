/**
 * PrescriptionsPage - Prescriptions list page.
 */

import { useState } from 'react'
import { usePrescriptions } from '../hooks/usePrescriptions'
import { useAuth } from '../hooks/useAuth'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { PrescriptionList } from '../components/prescriptions/PrescriptionList'
import { PrescriptionForm } from '../components/prescriptions/PrescriptionForm'
import './PrescriptionsPage.css'

export const PrescriptionsPage = () => {
  const { prescriptionList } = usePrescriptions()
  const { role } = useAuth()
  const [showCreateForm, setShowCreateForm] = useState(false)

  const isDoctor = role === 'doctor'

  const handleCreateSuccess = () => {
    setShowCreateForm(false)
    // Prescriptions will auto-refresh via the hook
  }

  return (
    <div className="prescriptions-page" data-state={prescriptionList.type}>
      <div className="page-header">
        <h1>Prescriptions</h1>
        {isDoctor && (
          <button
            data-testid="create-prescription"
            className="create-button"
            onClick={() => setShowCreateForm(true)}
          >
            Create Prescription
          </button>
        )}
      </div>

      {showCreateForm && (
        <PrescriptionForm
          onSuccess={handleCreateSuccess}
          onCancel={() => setShowCreateForm(false)}
        />
      )}

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
