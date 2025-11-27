/**
 * Header component - Top navigation bar.
 */

import { useAuth } from '../../hooks/useAuth'
import { LogoutButton } from '../auth/LogoutButton'
import './Header.css'

export const Header = () => {
  const { authState } = useAuth()

  const userEmail =
    authState.type === 'Authenticated' ? authState.email : null
  const userRole =
    authState.type === 'Authenticated' ? authState.role : null

  return (
    <header className="header">
      <div className="header-brand">
        <h1 className="header-title">HealthHub</h1>
      </div>

      {userEmail && (
        <div className="header-user">
          <span className="user-info">
            {userEmail}
            {userRole && <span className="user-role">{userRole}</span>}
          </span>
          <LogoutButton />
        </div>
      )}
    </header>
  )
}
