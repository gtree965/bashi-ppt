import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// NOTE: window.EXCALIDRAW_ASSET_PATH is set in index.html <head> (before any module
// loads) so Excalidraw resolves its self-hosted fonts from /fonts at export time.

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
