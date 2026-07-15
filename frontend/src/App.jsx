import { useCallback, useEffect, useRef, useState } from 'react'
import { createJob, deleteJob, extractJob, listJobs, login, register } from './api'
import Mascot from './Mascot'

const EMPTY_DRAFT = {
  url: '',
  title: '',
  company: '',
  description: '',
  deadline: '',
  location: '',
  source: '',
}

// A single-line http(s) link is treated as a URL to fetch; anything else
// (multi-line paste, plain text) is sent to the backend as pasted text —
// see PRD Task 2.2.
const URL_INPUT_RE = /^https?:\/\/\S+$/i

function timeAgo(isoUtc) {
  const then = new Date(`${isoUtc.replace(' ', 'T')}Z`)
  const seconds = Math.max(0, (Date.now() - then.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = seconds / 60
  if (minutes < 60) return `${Math.floor(minutes)}m ago`
  const hours = minutes / 60
  if (hours < 24) return `${Math.floor(hours)}h ago`
  const days = hours / 24
  if (days < 30) return `${Math.floor(days)}d ago`
  return then.toLocaleDateString()
}

function deadlineInfo(deadline) {
  if (!deadline) return null
  const date = new Date(deadline)
  if (Number.isNaN(date.getTime())) return { label: `Apply by ${deadline}`, tone: 'ok' }
  const msLeft = date.getTime() - Date.now()
  const daysLeft = Math.ceil(msLeft / 86400000)
  const pretty = date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  if (daysLeft < 0) return { label: `Closed ${pretty}`, tone: 'expired' }
  if (daysLeft <= 7) return { label: `Apply by ${pretty} · ${daysLeft}d left`, tone: 'soon' }
  return { label: `Apply by ${pretty}`, tone: 'ok' }
}

function JobCard({ job, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const deadline = deadlineInfo(job.deadline)
  const longDescription = job.description.length > 260

  return (
    <article className="job-card">
      <div className="job-card-head">
        <div>
          <h3 className="job-title">
            <a href={job.url} target="_blank" rel="noreferrer">
              {job.title}
            </a>
          </h3>
          <div className="job-meta">
            {job.company && <span className="company">{job.company}</span>}
            {job.location && <span className="dot-sep">{job.location}</span>}
            {job.source && <span className="dot-sep source">{job.source}</span>}
          </div>
        </div>
        <button
          className="icon-btn"
          title="Remove this job"
          onClick={() => onDelete(job)}
        >
          ✕
        </button>
      </div>

      {deadline && <span className={`deadline-badge ${deadline.tone}`}>{deadline.label}</span>}

      {job.description && (
        <p className={`job-description ${expanded ? 'expanded' : ''}`}>
          {expanded || !longDescription
            ? job.description
            : `${job.description.slice(0, 260).trimEnd()}…`}
        </p>
      )}
      {longDescription && (
        <button className="link-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}

      <footer className="job-card-foot">
        <span className="shared-by">
          <span className="avatar" aria-hidden="true">
            {(job.shared_by || 'A').trim().charAt(0).toUpperCase()}
          </span>
          Shared by <strong>{job.shared_by}</strong> · {timeAgo(job.created_at)}
        </span>
        <a className="apply-btn" href={job.url} target="_blank" rel="noreferrer">
          Apply ↗
        </a>
      </footer>
    </article>
  )
}

export default function App() {
  // Real account (name + bcrypt-hashed password, PRD Task 3.1): {id, name}
  // from POST /api/auth/register or /api/auth/login, remembered in
  // localStorage — no session/token beyond that.
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('appliora_user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [authMode, setAuthMode] = useState('login') // 'login' | 'register'
  const [loginName, setLoginName] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [linkInput, setLinkInput] = useState('')
  const [fetching, setFetching] = useState(false)
  const [draft, setDraft] = useState(null)
  const [draftNotes, setDraftNotes] = useState([])
  const [draftConfidence, setDraftConfidence] = useState({})
  const [saving, setSaving] = useState(false)
  const [jobs, setJobs] = useState([])
  const [search, setSearch] = useState('')
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
    if (user) localStorage.setItem('appliora_user', JSON.stringify(user))
    else localStorage.removeItem('appliora_user')
  }, [user])

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(''), 3500)
    return () => clearTimeout(timer)
  }, [toast])

  async function handleAuthSubmit(event) {
    event.preventDefault()
    if (!loginName.trim() || !loginPassword.trim()) return
    setLoggingIn(true)
    setError('')
    try {
      const result =
        authMode === 'register'
          ? await register(loginName.trim(), loginPassword)
          : await login(loginName.trim(), loginPassword)
      setUser(result)
      setLoginName('')
      setLoginPassword('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  function handleSwitchUser() {
    setUser(null)
    setAuthMode('login')
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
    if (!draft?.url.trim()) {
      setError('Please add the job link before sharing.')
      return
    }
    if (!user) {
      setError('Please log in or sign up (top right) before sharing.')
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

  async function handleDelete(job) {
    if (!window.confirm(`Remove "${job.title}" from the board?`)) return
    try {
      await deleteJob(job.id)
      setJobs((current) => current.filter((item) => item.id !== job.id))
    } catch (err) {
      setError(err.message)
    }
  }

  const updateDraft = (field) => (event) =>
    setDraft((current) => ({ ...current, [field]: event.target.value }))

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
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" className="logo" />
          <div>
            <h1>Appliora</h1>
            <p className="tagline">Share jobs with friends — details fetched automatically</p>
          </div>
        </div>
        {user ? (
          <div className="identity">
            <span className="signed-in-as">
              Signed in as <strong>{user.name}</strong>
            </span>
            <button type="button" className="ghost small" onClick={handleSwitchUser}>
              Switch
            </button>
          </div>
        ) : (
          <form className="login-row" onSubmit={handleAuthSubmit}>
            <input
              placeholder="Your name"
              value={loginName}
              maxLength={80}
              onChange={(event) => setLoginName(event.target.value)}
            />
            <input
              type="password"
              placeholder="Password"
              value={loginPassword}
              maxLength={200}
              onChange={(event) => setLoginPassword(event.target.value)}
            />
            <button
              type="submit"
              disabled={loggingIn || !loginName.trim() || !loginPassword.trim()}
            >
              {loggingIn
                ? authMode === 'register'
                  ? 'Creating…'
                  : 'Signing in…'
                : authMode === 'register'
                ? 'Sign up'
                : 'Log in'}
            </button>
            <button
              type="button"
              className="link-btn"
              onClick={() => {
                setAuthMode((mode) => (mode === 'login' ? 'register' : 'login'))
                setError('')
              }}
            >
              {authMode === 'register' ? 'Have an account? Log in' : "New here? Sign up"}
            </button>
          </form>
        )}
      </header>

      <main>
        <section className="share-box">
          <h2>Share a job</h2>
          <form className="link-row" onSubmit={handleFetch}>
            <textarea
              required
              rows={2}
              placeholder="Paste a job link, or the whole posting (email, Slack message, job text)…"
              value={linkInput}
              onChange={(event) => setLinkInput(event.target.value)}
            />
            <button type="submit" disabled={fetching || !linkInput.trim()}>
              {fetching
                ? 'Fetching…'
                : URL_INPUT_RE.test(linkInput.trim())
                ? 'Fetch details'
                : 'Parse text'}
            </button>
          </form>

          {draft && (
            <form className="draft" onSubmit={handleShare}>
              {draftNotes.map((note) => (
                <p key={note} className="note">
                  {note}
                </p>
              ))}
              <div className="field-grid">
                <label>
                  Job link *
                  <input
                    required
                    type="url"
                    value={draft.url}
                    maxLength={2000}
                    placeholder="https://… the real apply link"
                    onChange={updateDraft('url')}
                  />
                </label>
                <label>
                  <span className="field-label-row">
                    Job title *
                    {draftConfidence.title === 'low' && (
                      <span className="confidence-flag" title="Guessed from the page — double-check this">
                        guessed
                      </span>
                    )}
                  </span>
                  <input
                    required
                    value={draft.title}
                    maxLength={300}
                    placeholder="e.g. Software Engineer II"
                    onChange={updateDraft('title')}
                  />
                </label>
                <label>
                  <span className="field-label-row">
                    Company
                    {draftConfidence.company === 'low' && (
                      <span className="confidence-flag" title="Guessed from the page — double-check this">
                        guessed
                      </span>
                    )}
                  </span>
                  <input
                    value={draft.company}
                    maxLength={200}
                    placeholder="e.g. Microsoft"
                    onChange={updateDraft('company')}
                  />
                </label>
                <label>
                  <span className="field-label-row">
                    Last date to apply
                    {draftConfidence.deadline === 'low' && (
                      <span className="confidence-flag" title="Guessed from the page — double-check this">
                        guessed
                      </span>
                    )}
                  </span>
                  <input
                    value={draft.deadline}
                    maxLength={60}
                    placeholder="YYYY-MM-DD"
                    onChange={updateDraft('deadline')}
                  />
                </label>
                <label>
                  <span className="field-label-row">
                    Location
                    {draftConfidence.location === 'low' && (
                      <span className="confidence-flag" title="Guessed from the page — double-check this">
                        guessed
                      </span>
                    )}
                  </span>
                  <input
                    value={draft.location}
                    maxLength={200}
                    placeholder="e.g. Bangalore, India"
                    onChange={updateDraft('location')}
                  />
                </label>
              </div>
              <label>
                Description
                <textarea
                  rows={5}
                  value={draft.description}
                  maxLength={6000}
                  placeholder="What's the role about?"
                  onChange={updateDraft('description')}
                />
              </label>
              <div className="draft-actions">
                <button type="submit" className="primary" disabled={saving}>
                  {saving ? 'Sharing…' : 'Share job'}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => {
                    setDraft(null)
                    setDraftNotes([])
                    setDraftConfidence({})
                  }}
                >
                  Cancel
                </button>
                <span className="sharing-as">
                  {user ? (
                    <>
                      Sharing as <strong>{user.name}</strong>
                    </>
                  ) : (
                    'Log in (top right) before sharing so friends know who shared this'
                  )}
                </span>
              </div>
            </form>
          )}
        </section>

        {error && <div className="banner error">{error}</div>}
        {toast && <div className="banner success">{toast}</div>}

        <section className="feed">
          <div className="feed-head">
            <h2>
              Shared jobs {jobs.length > 0 && <span className="count">{jobs.length}</span>}
            </h2>
            <input
              className="search-input"
              placeholder="Search title, company, friend…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          {loading && <p className="muted">Loading jobs…</p>}
          {!loading && jobs.length === 0 && (
            <div className="empty">
              <p>No jobs here yet.</p>
              <p className="muted">Paste a job link above to share the first one!</p>
            </div>
          )}
          <div className="job-list">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onDelete={handleDelete} />
            ))}
          </div>
        </section>
      </main>

      <footer className="pagefoot">
        Appliora · built for friends who job-hunt together
      </footer>

      <Mascot mood={mascotMood} message={mascotMessage} />
    </div>
  )
}
