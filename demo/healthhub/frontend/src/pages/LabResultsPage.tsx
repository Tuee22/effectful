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
    <div className="lab-results-page" data-state={labResultList.type}>
      <div className="page-header">
        <h1>Lab Results</h1>
      </div>

      <RemoteDataRenderer
        data={labResultList}
        notAsked={() => (
          <p className="page-empty" data-testid="lab-result-empty">
            Loading lab results...
          </p>
        )}
        loading={() => (
          <p className="page-empty" data-testid="lab-result-empty">
            Loading lab results...
          </p>
        )}
        success={(labResults) => <LabResultList labResults={labResults} />}
        failure={() => (
          <p className="page-empty" data-testid="lab-result-empty">
            Unable to load lab results right now.
          </p>
        )}
      />
    </div>
  )
}
