/**
 * LabResultsPage - Lab results list page.
 */

import { useLabResults } from '../hooks/useLabResults'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { LabResultList } from '../components/lab-results/LabResultList'
import './LabResultsPage.css'

export const LabResultsPage = () => {
  const { labResultList } = useLabResults()

  return (
    <div className="lab-results-page">
      <div className="page-header">
        <h1>Lab Results</h1>
      </div>

      <RemoteDataRenderer
        data={labResultList}
        notAsked={() => (
          <p className="page-empty">
            No lab results loaded. Refresh the page to load lab results.
          </p>
        )}
        success={(labResults) => <LabResultList labResults={labResults} />}
      />
    </div>
  )
}
