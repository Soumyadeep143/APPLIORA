import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Landing from './Landing'
import './index.css'

// Distinct pages (PRD.md Task 6.4), not sections on one long scroll:
// 'home' (Landing's marketing sections), 'board' (Browse Jobs), 'share'
// (Add Job), 'login', 'signup', and 'admin' (PRD.md Task 6.5, admin-only).
// Landing's header is the one persistent nav across all of them; App's own
// header (identity bar) shows on the app-side views. `search` lives here
// so Landing's hero search box can drive App's job-board filter directly.
// `user` is mirrored up from App (which still owns the real read/write
// state — see App.jsx's onUserChange effect) so Landing's nav can show an
// Admin link without App having to hand off ownership of auth state.
function Root() {
  const [search, setSearch] = useState('')
  const [activeView, setActiveView] = useState('home')
  const [user, setUser] = useState(null)

  function searchFromLanding(query) {
    setSearch(query)
    setActiveView('board')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToView(view) {
    setActiveView(view)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <>
      <Landing
        activeView={activeView}
        onNavigate={goToView}
        onSearch={searchFromLanding}
        user={user}
      />
      <App
        activeView={activeView}
        onNavigate={goToView}
        search={search}
        onSearchChange={setSearch}
        onUserChange={setUser}
      />
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
