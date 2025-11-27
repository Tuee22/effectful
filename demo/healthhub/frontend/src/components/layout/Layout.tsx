/**
 * Layout component - Main application layout.
 * Uses React Router Outlet for nested routes.
 */

import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import './Layout.css'

export const Layout = () => (
  <div className="layout">
    <Header />
    <div className="layout-body">
      <Sidebar />
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  </div>
)
