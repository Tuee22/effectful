/**
 * PatientList component - List of patients.
 */

import { Link } from 'react-router-dom'
import { Patient, patientGetFullName, getAge } from '../../models'
import './PatientList.css'

interface PatientListProps {
  readonly patients: readonly Patient[]
}

export const PatientList = ({ patients }: PatientListProps) => {
  if (patients.length === 0) {
    return (
      <div className="patient-list-empty">
        <p>No patients found.</p>
      </div>
    )
  }

  return (
    <div className="patient-list">
      <table className="patient-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Age</th>
            <th>Blood Type</th>
            <th>Insurance ID</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient) => (
            <tr key={patient.id}>
              <td className="patient-name">{patientGetFullName(patient)}</td>
              <td>{getAge(patient)} years</td>
              <td>{patient.bloodType ?? 'Unknown'}</td>
              <td>{patient.insuranceId ?? 'N/A'}</td>
              <td>
                <Link
                  to={`/patients/${patient.id}`}
                  className="patient-view-link"
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
