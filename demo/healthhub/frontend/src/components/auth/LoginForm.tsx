/**
 * LoginForm component - Login form with validation.
 */

import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { isOk } from '../../algebraic/Result'
import { getErrorMessage } from '../../models/Auth'
import './LoginForm.css'

export const LoginForm = () => {
  const { authState, login, clearError } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    const result = await login(email, password)

    if (!isOk(result)) {
      setIsSubmitting(false)
    }
  }

  const error =
    authState.type === 'AuthenticationFailed'
      ? getErrorMessage(authState.error)
      : null

  const isLoading = authState.type === 'Authenticating' || isSubmitting

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <h2 className="login-title">Sign in to HealthHub</h2>

      {error && (
        <div className="login-error">
          {error}
          <button type="button" className="error-dismiss" onClick={clearError}>
            &times;
          </button>
        </div>
      )}

      <div className="form-group">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          required
          disabled={isLoading}
          autoComplete="email"
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter your password"
          required
          disabled={isLoading}
          autoComplete="current-password"
        />
      </div>

      <button type="submit" className="login-button" disabled={isLoading}>
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}
