/**
 * ErrorDisplay component - Show error messages.
 */

import './ErrorDisplay.css'

interface ErrorDisplayProps {
  readonly title?: string
  readonly message: string
  readonly onRetry?: () => void
}

export const ErrorDisplay = ({
  title = 'Error',
  message,
  onRetry,
}: ErrorDisplayProps) => (
  <div className="error-display">
    <div className="error-icon">!</div>
    <h3 className="error-title">{title}</h3>
    <p className="error-message">{message}</p>
    {onRetry && (
      <button className="error-retry" onClick={onRetry}>
        Try Again
      </button>
    )}
  </div>
)
