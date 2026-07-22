import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createJob,
  deleteJob,
  extractJob,
  listJobs,
  login,
  register,
  toggleReaction,
  updateJob,
} from './api'
import AddJobPage from './AddJobPage'
import AdminPage from './AdminPage'
import BrowseJobsPage from './BrowseJobsPage'
import LeaderboardPage from './LeaderboardPage'
import LoginPage from './LoginPage'
import { getPasswordError } from './passwordRules'
import SignupPage from './SignupPage'
import ProfilePage from './ProfilePage'
import PublicProfilePage from './PublicProfilePage'
import SuperAdminPage from './SuperAdminPage'
import Mascot from './Mascot'

// A single-line http(s) link is treated as a URL to fetch; anything else
// (multi-line paste, plain text) is sent to the backend as pasted text —
// see PRD Task 2.2. AddJobPage has its own copy of this (same value) for
// its button-label logic — kept independent rather than shared across
// files for one regex, per PRD.md Task 6.4's page-file split.
const URL_INPUT_RE = /^https?:\/\/\S+$/i

// Success-pause duration (Mascot.jsx's happy mood) before navigating away
// on a successful login/signup — long enough to actually see, short
// enough not to feel like a delay.
const SUCCESS_PAUSE_MS = 700
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export default function App({
  activeView,
  onNavigate,
  search,
  onSearchChange,
  user,
  setUser,
  viewedProfileUserId,
  onViewProfile,
}) {
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
  // Brief happy-mascot beat before navigating away on success (Mascot.jsx)
  // — without this, a successful login/signup redirects immediately and
  // the reaction is never actually visible.
  const [signupSucceeded, setSignupSucceeded] = useState(false)
  const [loginSucceeded, setLoginSucceeded] = useState(false)
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

  // Signed-out visitors can see Home (including Trending) but not the real
  // Browse Jobs / Add Job / Profile / Leaderboard pages (PRD.md Task 6.8, a
  // reversal of the earlier "browse without signing in" call) — bounced to
  // Login instead. A render-phase redirect would be a React anti-pattern
  // (side effect during render), hence the effect rather than an early
  // return that itself calls onNavigate.
  useEffect(() => {
    if (
      !user &&
      (activeView === 'board' ||
        activeView === 'share' ||
        activeView === 'profile' ||
        activeView === 'leaderboard' ||
        activeView === 'public-profile')
    ) {
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
    const passwordError = getPasswordError(signupPassword)
    if (passwordError) {
      setError(passwordError)
      return
    }
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
      setSignupSucceeded(true)
      await wait(SUCCESS_PAUSE_MS)
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
      setSignupSucceeded(false)
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
    // Clears a leftover toast from an earlier action (e.g. the signup
    // redirect's "Successfully signed up!") so Mascot.jsx can't show a
    // false happy reaction for a login attempt that hasn't resolved yet.
    setToast('')
    try {
      const result = await login(loginUsername.trim(), loginPassword)
      setUser(result)
      setLoginSucceeded(true)
      await wait(SUCCESS_PAUSE_MS)
      setLoginUsername('')
      setLoginPassword('')
      setToast('Successfully logged in!')
      onNavigate('board')
      setLoginSucceeded(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  // Logout lives on the Profile page now (PRD.md Task 6.12), not a navbar
  // Switch button — ProfilePage's own modal handles the typed YES/Y
  // confirmation before this ever gets called, so this is just the actual
  // sign-out action.
  function handleLogout() {
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

  // Admin-only server-side too (PRD.md Task 6.10) — JobEditForm's own Save
  // button only renders for admins, so a non-admin can't reach this path
  // anyway. Deliberately doesn't catch here: JobEditForm awaits this and
  // shows the error inline in its own form instead of the page-level
  // banner, same as CommentThread does with postComment.
  async function handleModify(jobId, fields) {
    const updated = await updateJob(jobId, fields, user.id)
    setJobs((current) => current.map((item) => (item.id === jobId ? updated : item)))
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
  // real board/share/leaderboard content for a split second before the
  // effect fires.
  if (
    !user &&
    (activeView === 'board' ||
      activeView === 'share' ||
      activeView === 'leaderboard' ||
      activeView === 'public-profile')
  )
    return null

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
        succeeded={loginSucceeded}
        onSubmit={handleLoginSubmit}
        onGoToSignup={() => {
          setError('')
          setLoginSucceeded(false)
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
        succeeded={signupSucceeded}
        onSubmit={handleSignupSubmit}
        onGoToLogin={() => {
          setError('')
          setSignupSucceeded(false)
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
    return <ProfilePage user={user} onLogout={handleLogout} onUpdate={setUser} />
  }

  if (activeView === 'public-profile') {
    if (!user) return null // guard effect above redirects to Login
    return <PublicProfilePage userId={viewedProfileUserId} />
  }

  if (activeView === 'leaderboard') {
    return <LeaderboardPage user={user} onViewProfile={onViewProfile} />
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

  // Identity/reminders/switch live in Landing's persistent header now
  // (PRD.md Task 6.10) — it's the one nav shown on every page, so repeating
  // an identity bar here was redundant and, per that task, explicitly
  // shouldn't show on Browse Jobs/Add Job at all.
  return (
    <div className="page" id="app">
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
            onModify={handleModify}
            onReact={handleReact}
            onCommentCountChange={handleCommentCountChange}
            onViewProfile={onViewProfile}
          />
        )}
      </main>

      <footer className="pagefoot">DevCareer · built for friends who job-hunt together</footer>

      <Mascot mood={mascotMood} message={mascotMessage} />
    </div>
  )
}
