/**
 * main.tsx - Application entry point.
 * Renders the React app to the DOM.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './index.css'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('Root element not found. Ensure index.html contains <div id="root"></div>')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)
