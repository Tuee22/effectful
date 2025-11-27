/**
 * Sidebar component - Navigation sidebar.
 */

import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import type { UserRole } from '../../models/Auth'
import './Sidebar.css'

interface NavItem {
  readonly path: string
  readonly label: string
  readonly roles: readonly UserRole[]
}

const navItems: readonly NavItem[] = [
  { path: '/', label: 'Dashboard', roles: ['patient', 'doctor', 'admin'] },
  { path: '/appointments', label: 'Appointments', roles: ['patient', 'doctor', 'admin'] },
  { path: '/patients', label: 'Patients', roles: ['doctor', 'admin'] },
  { path: '/prescriptions', label: 'Prescriptions', roles: ['patient', 'doctor', 'admin'] },
  { path: '/lab-results', label: 'Lab Results', roles: ['patient', 'doctor', 'admin'] },
  { path: '/invoices', label: 'Invoices', roles: ['patient', 'doctor', 'admin'] },
]

export const Sidebar = () => {
  const { role } = useAuth()

  const visibleItems = navItems.filter(
    (item) => role !== null && item.roles.includes(role)
  )

  return (
    <nav className="sidebar">
      <ul className="sidebar-nav">
        {visibleItems.map((item) => (
          <li key={item.path} className="sidebar-item">
            <NavLink
              to={item.path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
