import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { RegistrationForm } from '../components/auth/RegistrationForm'
import './LoginPage.css'

export const RegisterPage = () => {
  const { isAuthenticated, hasHydrated } = useAuth()
  const navigate = useNavigate()

  // Redirect if already authenticated
  useEffect(() => {
    if (hasHydrated && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [hasHydrated, isAuthenticated, navigate])

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>HealthHub</h1>
          <p>Healthcare Management Portal</p>
        </div>
        <RegistrationForm />
      </div>
    </div>
  )
}
