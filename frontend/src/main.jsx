import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Landing from './Landing'
import './index.css'

// Distinct pages (PRD.md Task 6.4), not sections on one long scroll:
// 'home' (Landing's marketing sections), 'board' (Browse Jobs), 'share'
// (Add Job), 'login', 'signup', 'profile', 'leaderboard', 'admin' and
// 'superadmin'. Landing's header is the one persistent nav across all of
// them (PRD.md Task 6.10 moved identity/reminders/switch there and out of
// App's own page-level header, which only ever showed on board/share
// anyway). `search` lives here so Landing's hero search box can drive
// App's job-board filter directly.
//
// `user` is owned here (not App) — Landing's header shows identity/
// reminders/switch on every page, App's board/share/profile/leaderboard
// views need it too, and Landing+App are siblings, so the account that
// reads AND writes it has to sit above both (PRD.md Task 6.10; previously
// App owned it and mirrored a read-only copy up to Root for Landing's nav).
function Root() {
  const [search, setSearch] = useState('')
  const [activeView, setActiveView] = useState('home')
  // Whose profile 'public-profile' should render (PRD.md Task 6.13) —
  // opened from a Leaderboard row or a job's "Shared by" name. A separate
  // piece of state from `user` (the signed-in account) since these are
  // usually two different people.
  const [viewedProfileUserId, setViewedProfileUserId] = useState(null)
  // Real account (name + bcrypt-hashed password, PRD Task 3.1): {id, name,
  // ...} from POST /api/auth/register or /api/auth/login, remembered in
  // localStorage — no session/token beyond that.
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('devcareer_user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  useEffect(() => {
    if (user) localStorage.setItem('devcareer_user', JSON.stringify(user))
    else localStorage.removeItem('devcareer_user')
  }, [user])

  function searchFromLanding(query) {
    setSearch(query)
    setActiveView('board')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToView(view) {
    setActiveView(view)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Clicking your own name/row goes to the real (editable) Profile page
  // instead of the read-only public one — no reason to show yourself the
  // stranger's-eye view when the editable page is one click away anyway.
  function viewProfile(userId) {
    if (user && userId === user.id) {
      goToView('profile')
      return
    }
    setViewedProfileUserId(userId)
    goToView('public-profile')
  }

  return (
    <>
      <Landing
        activeView={activeView}
        onNavigate={goToView}
        onSearch={searchFromLanding}
        user={user}
        setUser={setUser}
      />
      <App
        activeView={activeView}
        onNavigate={goToView}
        search={search}
        onSearchChange={setSearch}
        user={user}
        setUser={setUser}
        viewedProfileUserId={viewedProfileUserId}
        onViewProfile={viewProfile}
      />
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
