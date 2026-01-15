/**
 * LogoutButton component - Button to log out.
 */

import { useAuth } from '../../hooks/useAuth'
import './LogoutButton.css'

export const LogoutButton = () => {
  const { logout } = useAuth()

  return (
    <button className="logout-button" onClick={logout}>
      Sign Out
    </button>
  )
}
