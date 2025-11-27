/**
 * PrescriptionList component - List of prescriptions.
 */

import { Link } from 'react-router-dom'
import { Prescription, prescriptionGetStatus, prescriptionGetStatusLabel, prescriptionGetStatusColor } from '../../models'
import './PrescriptionList.css'

interface PrescriptionListProps {
  readonly prescriptions: readonly Prescription[]
}

interface StatusBadgeProps {
  readonly prescription: Prescription
}

const StatusBadge = ({ prescription }: StatusBadgeProps) => {
  const status = prescriptionGetStatus(prescription)
  return (
    <span
      className="prescription-status-badge"
      style={{ backgroundColor: prescriptionGetStatusColor(status) }}
    >
      {prescriptionGetStatusLabel(status)}
    </span>
  )
}

export const PrescriptionList = ({ prescriptions }: PrescriptionListProps) => {
  if (prescriptions.length === 0) {
    return (
      <div className="prescription-list-empty">
        <p>No prescriptions found.</p>
      </div>
    )
  }

  return (
    <div className="prescription-list">
      <table className="prescription-table">
        <thead>
          <tr>
            <th>Medication</th>
            <th>Dosage</th>
            <th>Frequency</th>
            <th>Duration</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {prescriptions.map((prescription) => (
            <tr key={prescription.id}>
              <td className="prescription-medication">{prescription.medication}</td>
              <td>{prescription.dosage}</td>
              <td>{prescription.frequency}</td>
              <td>{prescription.durationDays} days</td>
              <td>
                <StatusBadge prescription={prescription} />
              </td>
              <td>
                <Link
                  to={`/prescriptions/${prescription.id}`}
                  className="prescription-view-link"
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
