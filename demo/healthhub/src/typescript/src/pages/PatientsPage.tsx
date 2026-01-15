/**
 * PatientsPage - Patients list page (doctor/admin only).
 */

import { usePatients } from '../hooks/usePatients'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { PatientList } from '../components/patients/PatientList'
import './PatientsPage.css'

export const PatientsPage = () => {
  const { patientList } = usePatients()

  return (
    <div className="patients-page" data-state={patientList.type}>
      <div className="page-header">
        <h1>Patients</h1>
      </div>

      <RemoteDataRenderer
        data={patientList}
        notAsked={() => (
          <p className="page-empty">
            No patients loaded. Refresh the page to load patients.
          </p>
        )}
        success={(patients) => <PatientList patients={patients} />}
      />
    </div>
  )
}
