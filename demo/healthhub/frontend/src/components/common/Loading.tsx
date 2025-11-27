/**
 * Loading component - Spinner for loading states.
 */

import './Loading.css'

interface LoadingProps {
  readonly message?: string
}

export const Loading = ({ message = 'Loading...' }: LoadingProps) => (
  <div className="loading">
    <div className="loading-spinner" />
    <p className="loading-message">{message}</p>
  </div>
)
