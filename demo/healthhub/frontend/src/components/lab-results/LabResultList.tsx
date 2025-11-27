/**
 * LabResultList component - List of lab results.
 */

import { Link } from 'react-router-dom'
import { LabResult, labResultFormatDate } from '../../models'
import './LabResultList.css'

interface LabResultListProps {
  readonly labResults: readonly LabResult[]
}

interface CriticalBadgeProps {
  readonly critical: boolean
}

const CriticalBadge = ({ critical }: CriticalBadgeProps) => {
  if (!critical) return null
  return (
    <span className="lab-result-critical-badge">
      Critical
    </span>
  )
}

interface ReviewedBadgeProps {
  readonly reviewed: boolean
}

const ReviewedBadge = ({ reviewed }: ReviewedBadgeProps) => {
  return (
    <span
      className="lab-result-reviewed-badge"
      style={{ backgroundColor: reviewed ? '#10b981' : '#f59e0b' }}
    >
      {reviewed ? 'Reviewed' : 'Pending Review'}
    </span>
  )
}

export const LabResultList = ({ labResults }: LabResultListProps) => {
  if (labResults.length === 0) {
    return (
      <div className="lab-result-list-empty">
        <p>No lab results found.</p>
      </div>
    )
  }

  return (
    <div className="lab-result-list">
      <table className="lab-result-table">
        <thead>
          <tr>
            <th>Test Type</th>
            <th>Date</th>
            <th>Critical</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {labResults.map((labResult) => (
            <tr key={labResult.id}>
              <td className="lab-result-test-type">{labResult.testType}</td>
              <td>{labResultFormatDate(labResult.createdAt)}</td>
              <td>
                <CriticalBadge critical={labResult.critical} />
              </td>
              <td>
                <ReviewedBadge reviewed={labResult.reviewedByDoctor} />
              </td>
              <td>
                <Link
                  to={`/lab-results/${labResult.id}`}
                  className="lab-result-view-link"
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
