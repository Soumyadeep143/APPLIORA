import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createJob,
  deleteJob,
  extractJob,
  getLeaderboard,
  listJobs,
  login,
  register,
  toggleReaction,
  updateNotificationSettings,
} from './api'
import AddJobPage from './AddJobPage'
import AdminPage from './AdminPage'
import BrowseJobsPage from './BrowseJobsPage'
import LoginPage from './LoginPage'
import SignupPage from './SignupPage'
import ProfilePage from './ProfilePage'
import SuperAdminPage from './SuperAdminPage'
import Mascot from './Mascot'

// A single-line http(s) link is treated as a URL to fetch; anything else
// (multi-line paste, plain text) is sent to the backend as pasted text —
// see PRD Task 2.2. AddJobPage has its own copy of this (same value) for
// its button-label logic — kept independent rather than shared across
// files for one regex, per PRD.md Task 6.4's page-file split.
const URL_INPUT_RE = /^https?:\/\/\S+$/i

function NotificationSettings({ user, onUpdate }) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState(user.email || '')
  const [optIn, setOptIn] = useState(!!user.reminders_opt_in)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  // Click anywhere outside the panel closes it — it was previously only
  // dismissible via the toggle button, so it could sit open indefinitely
  // on top of the page (see the "go down" bug report: saving didn't close
  // it either, fixed below in handleSave). Shared with RankPanel below,
  // which uses the same popover pattern.
  const wrapperRef = useOutsideClose(open, setOpen)

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const updated = await updateNotificationSettings(user.id, email.trim(), optIn)
      onUpdate(updated)
      setSaved(true)
      setTimeout(() => {
        setSaved(false)
        setOpen(false)
      }, 900)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="notif-settings" ref={wrapperRef}>
      <button type="button" className="ghost small" onClick={() => setOpen((value) => !value)}>
        🔔 Reminders
      </button>
      {open && (
        <form className="notif-panel" onSubmit={handleSave}>
          <label>
            Email
            <input
              type="email"
              value={email}
              maxLength={200}
              placeholder="you@example.com"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="notif-checkbox">
            <input
              type="checkbox"
              checked={optIn}
              onChange={(event) => setOptIn(event.target.checked)}
            />
            Email me daily about deadlines closing soon and new jobs friends share
          </label>
          {error && <p className="comment-error">{error}</p>}
          <button type="submit" disabled={saving}>
            {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save'}
          </button>
        </form>
      )}
    </div>
  )
}

function useOutsideClose(open, setOpen) {
  const wrapperRef = useRef(null)
  useEffect(() => {
    if (!open) return
    function handleOutsideClick(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [open, setOpen])
  return wrapperRef
}

function RankPanel({ user }) {
  const [open, setOpen] = useState(false)
  const [board, setBoard] = useState(null)
  const [copied, setCopied] = useState(false)
  const wrapperRef = useOutsideClose(open, setOpen)

  useEffect(() => {
    if (!open || board !== null) return
    getLeaderboard()
      .then(setBoard)
      .catch(() => setBoard([]))
  }, [open, board])

  async function handleCopyCode() {
    try {
      await navigator.clipboard.writeText(user.referral_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard permission denied — the code is still shown to copy by hand */
    }
  }

  return (
    <div className="notif-settings" ref={wrapperRef}>
      <button type="button" className="ghost small" onClick={() => setOpen((value) => !value)}>
        🏆 Rank {user.rank_points > 0 && `· ${user.rank_points}`}
      </button>
      {open && (
        <div className="notif-panel rank-panel">
          <p className="rank-points">
            <strong>{user.rank_points}</strong> points
          </p>
          <label>
            Your referral code — friends who sign up with it earn you points
            <span className="referral-code-row">
              <code>{user.referral_code}</code>
              <button type="button" className="icon-btn small" onClick={handleCopyCode}>
                {copied ? 'Copied ✓' : 'Copy'}
              </button>
            </span>
          </label>
          <p className="rank-leaderboard-title">Leaderboard</p>
          {board === null ? (
            <p className="muted">Loading…</p>
          ) : (
            <ol className="rank-leaderboard">
              {board.map((row) => (
                <li key={row.id} className={row.id === user.id ? 'me' : ''}>
                  <span>{row.name}</span>
                  <span>{row.rank_points}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}

export default function App({ activeView, onNavigate, search, onSearchChange, onUserChange }) {
  // Real account (name + bcrypt-hashed password, PRD Task 3.1): {id, name}
  // from POST /api/auth/register or /api/auth/login, remembered in
  // localStorage — no session/token beyond that.
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('devcareer_user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  // Login and Signup (PRD.md Task 6.7) are separate pages with separate
  // field sets now, not one form with a mode toggle — separate state per
  // form rather than one shared set that only some fields use.
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [signupUsername, setSignupUsername] = useState('')
  const [signupName, setSignupName] = useState('')
  const [signupEmail, setSignupEmail] = useState('')
  const [signupPassword, setSignupPassword] = useState('')
  const [signupReferralCode, setSignupReferralCode] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [linkInput, setLinkInput] = useState('')
  const [fetching, setFetching] = useState(false)
  const [draft, setDraft] = useState(null)
  const [draftNotes, setDraftNotes] = useState([])
  const [draftConfidence, setDraftConfidence] = useState({})
  const [saving, setSaving] = useState(false)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  // Monotonic id so a slow, older /api/jobs response can never
  // overwrite the result of a newer one (e.g. share vs. search races).
  const refreshSeq = useRef(0)

  const refresh = useCallback(async (query = '') => {
    const seq = ++refreshSeq.current
    try {
      const result = await listJobs(query)
      if (seq !== refreshSeq.current) return
      setJobs(result)
      setError('')
    } catch (err) {
      if (seq !== refreshSeq.current) return
      setError(`Could not load jobs: ${err.message}`)
    } finally {
      if (seq === refreshSeq.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    const timer = setTimeout(() => refresh(search), 300)
    return () => clearTimeout(timer)
  }, [search, refresh])

  useEffect(() => {
    if (user) localStorage.setItem('devcareer_user', JSON.stringify(user))
    else localStorage.removeItem('devcareer_user')
  }, [user])

  // Mirrors this component's user state up to Root — App still owns the
  // real read/write cycle (login/register/switch all happen here), but
  // Landing's nav needs to know is_admin to show/hide the Admin link, and
  // Landing and App are siblings under Root, not parent/child.
  useEffect(() => {
    onUserChange(user)
  }, [user, onUserChange])

  // Signed-out visitors can see Home (including Trending) but not the real
  // Browse Jobs / Add Job / Profile pages (PRD.md Task 6.8, a reversal of
  // the earlier "browse without signing in" call) — bounced to Login
  // instead. A render-phase redirect would be a React anti-pattern (side
  // effect during render), hence the effect rather than an early return
  // that itself calls onNavigate.
  useEffect(() => {
    if (!user && (activeView === 'board' || activeView === 'share' || activeView === 'profile')) {
      onNavigate('login')
    }
  }, [user, activeView, onNavigate])

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(''), 3500)
    return () => clearTimeout(timer)
  }, [toast])

  async function handleSignupSubmit(event) {
    event.preventDefault()
    if (!signupUsername.trim() || !signupName.trim() || !signupEmail.trim() || !signupPassword.trim())
      return
    setLoggingIn(true)
    setError('')
    try {
      await register(
        signupUsername.trim(),
        signupName.trim(),
        signupEmail.trim(),
        signupPassword,
        signupReferralCode.trim()
      )
      // Deliberately doesn't sign the new account in (PRD.md Task 6.8) —
      // land on Login with the username already filled in so the only
      // thing left to type is the password just chosen.
      setLoginUsername(signupUsername.trim())
      setSignupUsername('')
      setSignupName('')
      setSignupEmail('')
      setSignupPassword('')
      setSignupReferralCode('')
      setToast('Successfully signed up! Log in to continue.')
      onNavigate('login')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault()
    if (!loginUsername.trim() || !loginPassword.trim()) return
    setLoggingIn(true)
    setError('')
    try {
      const result = await login(loginUsername.trim(), loginPassword)
      setUser(result)
      setLoginUsername('')
      setLoginPassword('')
      setToast('Successfully logged in!')
      onNavigate('board')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  function handleSwitchUser() {
    setUser(null)
    onNavigate('login')
  }

  async function handleFetch(event) {
    event.preventDefault()
    const value = linkInput.trim()
    if (!value) return
    setFetching(true)
    setError('')
    try {
      const meta = URL_INPUT_RE.test(value)
        ? await extractJob({ url: value })
        : await extractJob({ text: value })
      setDraft({
        url: meta.url,
        title: meta.title,
        company: meta.company,
        description: meta.description,
        deadline: meta.deadline,
        location: meta.location,
        source: meta.source,
        apply_email: meta.apply_email || '',
        apply_email_subject: meta.apply_email_subject || '',
      })
      setDraftNotes(meta.notes || [])
      setDraftConfidence(meta.field_confidence || {})
    } catch (err) {
      setError(err.message)
    } finally {
      setFetching(false)
    }
  }

  async function handleShare(event) {
    event.preventDefault()
    if (!draft?.title.trim()) {
      setError('Please add a job title before sharing.')
      return
    }
    if (!draft?.url.trim() && !draft?.apply_email.trim()) {
      setError('Please add a job link or an apply email before sharing.')
      return
    }
    if (!user) {
      setError('Please log in or sign up before sharing.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await createJob({ ...draft, user_id: user.id })
      setDraft(null)
      setDraftNotes([])
      setDraftConfidence({})
      setLinkInput('')
      setToast('Job shared with your friends 🎉')
      await refresh(search)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function handleCancelDraft() {
    setDraft(null)
    setDraftNotes([])
    setDraftConfidence({})
  }

  async function handleDelete(job) {
    // Admin-only server-side too (PRD.md Task 6.2) — this check is just
    // for the confirm-dialog UX; the JobCard delete button itself only
    // renders for admins, so a non-admin can't reach this path anyway.
    if (!user?.is_admin) return
    if (!window.confirm(`Remove "${job.title}" from the board?`)) return
    try {
      await deleteJob(job.id, user.id)
      setJobs((current) => current.filter((item) => item.id !== job.id))
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleReact(job, emoji) {
    if (!user) {
      setError('Please log in to react.')
      return
    }
    try {
      const reactions = await toggleReaction(job.id, user.id, emoji)
      setJobs((current) =>
        current.map((item) => (item.id === job.id ? { ...item, reactions } : item))
      )
    } catch (err) {
      setError(err.message)
    }
  }

  function handleCommentCountChange(jobId, delta) {
    setJobs((current) =>
      current.map((item) =>
        item.id === jobId ? { ...item, comment_count: item.comment_count + delta } : item
      )
    )
  }

  const updateDraft = (field) => (event) =>
    setDraft((current) => ({ ...current, [field]: event.target.value }))

  if (activeView === 'home') return null

  // Render-phase half of the redirect guard above — avoids a flash of the
  // real board/share content for a split second before the effect fires.
  if (!user && (activeView === 'board' || activeView === 'share')) return null

  if (activeView === 'login') {
    return (
      <LoginPage
        username={loginUsername}
        setUsername={setLoginUsername}
        password={loginPassword}
        setPassword={setLoginPassword}
        loading={loggingIn}
        error={error}
        toast={toast}
        onSubmit={handleLoginSubmit}
        onGoToSignup={() => {
          setError('')
          onNavigate('signup')
        }}
      />
    )
  }

  if (activeView === 'signup') {
    return (
      <SignupPage
        username={signupUsername}
        setUsername={setSignupUsername}
        name={signupName}
        setName={setSignupName}
        email={signupEmail}
        setEmail={setSignupEmail}
        password={signupPassword}
        setPassword={setSignupPassword}
        referralCode={signupReferralCode}
        setReferralCode={setSignupReferralCode}
        loading={loggingIn}
        error={error}
        onSubmit={handleSignupSubmit}
        onGoToLogin={() => {
          setError('')
          onNavigate('login')
        }}
      />
    )
  }

  if (activeView === 'admin') {
    // Server-side enforced too (every /api/admin/* call 403s a non-admin) —
    // this is just so a non-admin who somehow lands here (e.g. a stale
    // bookmark from before being demoted) sees a message, not a broken page.
    if (!user?.is_admin) {
      return (
        <div className="page" id="app">
          <p className="banner error" style={{ margin: '40px auto', maxWidth: 420 }}>
            Admin access required.
          </p>
        </div>
      )
    }
    return <AdminPage adminUserId={user.id} />
  }

  if (activeView === 'profile') {
    if (!user) return null // guard effect above redirects to Login
    return <ProfilePage user={user} />
  }

  if (activeView === 'superadmin') {
    // Server-side enforced too (every /api/superadmin/* call 403s a
    // non-superadmin) — this is UX polish, not the real gate.
    if (!user?.is_superadmin) {
      return (
        <div className="page" id="app">
          <p className="banner error" style={{ margin: '40px auto', maxWidth: 420 }}>
            Super admin access required.
          </p>
        </div>
      )
    }
    return <SuperAdminPage superadminUserId={user.id} />
  }

  // Applio the mascot follows the product story, frame by frame.
  let mascotMood = 'idle'
  let mascotMessage = ''
  if (fetching) {
    // the pasted link turns into docs + AI particles
    mascotMood = 'searching'
    mascotMessage = 'Reading the job page for you… ✨'
  } else if (saving) {
    mascotMood = 'searching'
    mascotMessage = 'Pinning it to the board…'
  } else if (error) {
    mascotMood = 'sad'
    mascotMessage = 'Hmm, that didn’t work. Mind checking the details?'
  } else if (toast) {
    // success: checkmark + confetti
    mascotMood = 'happy'
    mascotMessage = 'Shared! Your friends can see it now 🎉'
  } else if (draft) {
    // the extracted job card appears
    mascotMood = 'found'
    mascotMessage = draft.title
      ? 'Ta-da! Here’s the job card — give it a look, then hit Share.'
      : 'That page kept its secrets — fill the details in and share anyway!'
  } else if (!loading && jobs.length === 0 && !search) {
    // welcome: found a job? copy the link!
    mascotMood = 'waving'
    mascotMessage = "Hi, I'm Applio! Found a job you like? Paste the link and I'll fetch the details."
  }

  return (
    <div className="page" id="app">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" className="logo" />
          <div>
            <h1>DevCareer</h1>
            <p className="tagline">Share jobs with friends — details fetched automatically</p>
          </div>
        </div>
        {user ? (
          <div className="identity">
            <span className="signed-in-as">
              Signed in as <strong>{user.name}</strong>
            </span>
            <RankPanel user={user} />
            <NotificationSettings user={user} onUpdate={setUser} />
            <button type="button" className="ghost small" onClick={handleSwitchUser}>
              Switch
            </button>
          </div>
        ) : (
          <div className="identity">
            <span className="signed-in-as">Not signed in</span>
            <button type="button" className="ghost small" onClick={() => onNavigate('login')}>
              Log in
            </button>
            <button type="button" className="ghost small" onClick={() => onNavigate('signup')}>
              Sign up
            </button>
          </div>
        )}
      </header>

      <main>
        {activeView === 'share' && (
          <AddJobPage
            user={user}
            linkInput={linkInput}
            setLinkInput={setLinkInput}
            fetching={fetching}
            onFetch={handleFetch}
            draft={draft}
            draftNotes={draftNotes}
            draftConfidence={draftConfidence}
            updateDraft={updateDraft}
            onShare={handleShare}
            saving={saving}
            onCancelDraft={handleCancelDraft}
          />
        )}

        {error && <div className="banner error">{error}</div>}
        {toast && <div className="banner success">{toast}</div>}

        {activeView === 'board' && (
          <BrowseJobsPage
            jobs={jobs}
            loading={loading}
            search={search}
            onSearchChange={onSearchChange}
            user={user}
            onDelete={handleDelete}
            onReact={handleReact}
            onCommentCountChange={handleCommentCountChange}
          />
        )}
      </main>

      <footer className="pagefoot">DevCareer · built for friends who job-hunt together</footer>

      <Mascot mood={mascotMood} message={mascotMessage} />
    </div>
  )
}
