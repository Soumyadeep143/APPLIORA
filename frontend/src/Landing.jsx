import { useEffect, useState } from 'react'
import { listJobs } from './api'
import { deadlineInfo } from './dateUtils'
import './landing.css'

// Cycled by index — real jobs don't carry a color, so this just gives the
// trending strip some visual variety instead of one flat tone.
const ICON_GRADIENTS = [
  'linear-gradient(135deg,#4A90D9,#1E5AA8)',
  'linear-gradient(135deg,#FF8C42,#FF7A30)',
  'linear-gradient(135deg,#1E5AA8,#0F2942)',
]

const TRENDING_LIMIT = 10
// A handful of cards duplicated once already loops fine; below this the
// gap before the seam repeats is short enough to look janky, so the loop
// is padded out by repeating the fetched jobs rather than lengthening the
// single-pass list.
const TRENDING_MIN_FOR_SMOOTH_LOOP = 4

function trendingCardFromJob(job, index) {
  const info = deadlineInfo(job.deadline)
  let tag = null
  let tagClass = ''
  if (info?.tone === 'soon') {
    tag = 'Closing soon'
    tagClass = 'closing'
  } else if (info?.tone === 'expired') {
    tag = 'Closed'
    tagClass = 'closing'
  } else if (/remote/i.test(job.location || '')) {
    tag = 'Remote'
    tagClass = 'remote'
  }

  let deadlineLabel = ''
  if (info) {
    deadlineLabel =
      info.tone === 'expired'
        ? 'Closed'
        : info.tone === 'soon' && typeof info.daysLeft === 'number'
          ? `${info.daysLeft}d left`
          : info.label
  }

  return {
    id: job.id,
    title: job.title,
    company: [job.company, job.location].filter(Boolean).join(' · '),
    tag,
    tagClass,
    deadlineLabel,
    icon: ICON_GRADIENTS[index % ICON_GRADIENTS.length],
  }
}

const HOW_STEPS = [
  { num: 1, tone: 'blue', title: 'Paste a job link', desc: 'Any careers page or board URL works.' },
  {
    num: 2,
    tone: 'orange',
    title: 'Sign up, join the circle',
    desc: 'Create your account with just a name and password.',
  },
  { num: 3, tone: 'blue', title: 'React, comment, apply', desc: 'Get reminders before deadlines close.' },
]

// Reuses the same mark as frontend/public/favicon.svg (and App.jsx's
// in-app header logo) instead of re-embedding the SVG here, so there's one
// source of truth for the brand mark rather than two that can drift.
function DevCareerLogo({ size = 34 }) {
  return <img src="/favicon.svg" alt="" width={size} height={size} />
}

function TrendingStrip({ jobs, onCardClick }) {
  if (jobs === null) return null // still loading — nothing to show yet
  if (jobs.length === 0) {
    return <p className="trending-empty">No jobs shared yet — be the first to paste one.</p>
  }

  // Looped by rendering the list twice back to back and animating the
  // track exactly half its own width — duplicated again first if the
  // fetched set is too short for that seam to be unnoticeable.
  const looped = jobs.length < TRENDING_MIN_FOR_SMOOTH_LOOP ? [...jobs, ...jobs] : jobs
  const track = [...looped, ...looped]
  const duration = Math.max(looped.length * 5, 16)

  return (
    <div className="trending-marquee">
      <div className="trending-track" style={{ animationDuration: `${duration}s` }}>
        {track.map((job, index) => (
          <button
            key={`${job.id}-${index}`}
            type="button"
            className="trending-card"
            onClick={onCardClick}
          >
            <div className="trending-card-top">
              <div className="trending-icon" style={{ background: job.icon }} />
              {job.tag && <span className={`trending-tag ${job.tagClass}`}>{job.tag}</span>}
            </div>
            <div className="trending-title">{job.title}</div>
            {job.company && <div className="trending-company">{job.company}</div>}
            <div className="trending-foot">
              <span className="trending-deadline">{job.deadlineLabel}</span>
              <span className="trending-apply">Apply</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// activeView drives which page is showing (PRD.md Task 6.4: Browse Jobs /
// Add Job / Log in-Sign up are distinct pages, not scroll positions on one
// long page). This header is the one persistent nav across all of them.
export default function Landing({ activeView, onNavigate, onSearch, user }) {
  const [query, setQuery] = useState('')
  const [trendingJobs, setTrendingJobs] = useState(null)

  useEffect(() => {
    let cancelled = false
    function fetchTrending() {
      listJobs()
        .then((jobs) => {
          if (cancelled) return
          setTrendingJobs(jobs.slice(0, TRENDING_LIMIT).map(trendingCardFromJob))
        })
        .catch(() => {
          // Marketing page shouldn't break if the API hiccups — same
          // "empty over broken" principle the rest of the app follows.
          if (!cancelled) setTrendingJobs([])
        })
    }
    fetchTrending()
    // Real-time-ish freshness (PRD.md Task 6.6): re-runs on every
    // navigation to Home (so a job an admin just deleted elsewhere doesn't
    // linger here until someone happens to reload) and polls while Home is
    // actually the visible page — no point polling while a different page
    // is showing, nobody's looking at this section then.
    const interval = activeView === 'home' ? setInterval(fetchTrending, 20000) : null
    return () => {
      cancelled = true
      if (interval) clearInterval(interval)
    }
  }, [activeView])

  function handleSearch(event) {
    event.preventDefault()
    onSearch(query.trim())
  }

  function navLink(view, label) {
    return (
      <a
        href="#"
        className={activeView === view ? 'active' : ''}
        onClick={(event) => {
          event.preventDefault()
          onNavigate(view)
        }}
      >
        {label}
      </a>
    )
  }

  // "How it works"/"Trending" both live inside Home's marketing content,
  // which is only mounted when activeView === 'home' — if we're on a
  // different page, onNavigate('home') doesn't put that section in the DOM
  // until React re-renders, so scrolling to it in the same click handler
  // would silently no-op. Double rAF waits for that render (and the
  // browser's next layout pass) before scrolling; already on Home, it's a
  // plain instant scroll with no navigation jump first.
  function goToHomeSection(id) {
    if (activeView === 'home') {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
      return
    }
    onNavigate('home')
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
      })
    })
  }

  function homeSectionLink(id, label) {
    return (
      <a
        href="#"
        onClick={(event) => {
          event.preventDefault()
          goToHomeSection(id)
        }}
      >
        {label}
      </a>
    )
  }

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-logo" role="button" tabIndex={0} onClick={() => onNavigate('home')}>
          <DevCareerLogo />
          <span>DevCareer</span>
        </div>
        <nav className="landing-nav">
          <div className="landing-links">
            {navLink('board', 'Browse Jobs')}
            {navLink('share', 'Add Job')}
            {homeSectionLink('how-it-works', 'How it works')}
            {homeSectionLink('trending', 'Trending')}
            {user && navLink('profile', 'Profile')}
            {user?.is_admin && navLink('admin', '🛡️ Admin')}
            {user?.is_superadmin && navLink('superadmin', '👑 Super Admin')}
          </div>
          {user ? (
            <span className="landing-signed-in-as">Signed in as {user.name}</span>
          ) : (
            <>
              <a
                href="#"
                className="landing-loginlink"
                onClick={(event) => {
                  event.preventDefault()
                  onNavigate('login')
                }}
              >
                Log in
              </a>
              <a
                href="#"
                className="landing-btn-primary"
                onClick={(event) => {
                  event.preventDefault()
                  onNavigate('signup')
                }}
              >
                Sign up free
              </a>
            </>
          )}
        </nav>
      </header>

      {activeView === 'home' && (
        <>
          <section className="landing-hero">
            <div className="landing-blob landing-blob-a" aria-hidden="true" />
            <div className="landing-blob landing-blob-b" aria-hidden="true" />

            <div className="landing-badge">Built for job-hunting crews</div>
            <h1>
              Climb faster,
              <br />
              with your crew.
            </h1>
            <p>
              Paste a job link, DevCareer fills in the title, company and deadline — your circle
              reacts, comments and applies together.
            </p>

            <div className="landing-search">
              <form onSubmit={handleSearch}>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search Frontend, Backend, DevOps, ML…"
                  aria-label="Search jobs"
                />
                <button type="submit">Search</button>
              </form>
            </div>

            <div className="landing-stats">
              <div>
                <div className="landing-stat-num">1,200+</div>
                <div className="landing-stat-label">jobs shared</div>
              </div>
              <div>
                <div className="landing-stat-num">340</div>
                <div className="landing-stat-label">friend circles</div>
              </div>
              <div>
                <div className="landing-stat-num">58</div>
                <div className="landing-stat-label">companies posted</div>
              </div>
            </div>
          </section>

          <section className="landing-trending" id="trending">
            <div className="landing-section-head">
              <h2>Trending this week</h2>
              <a
                href="#"
                className="landing-viewall"
                onClick={(event) => {
                  event.preventDefault()
                  onNavigate('board')
                }}
              >
                View all →
              </a>
            </div>
            <TrendingStrip jobs={trendingJobs} onCardClick={() => onNavigate('board')} />
          </section>

          <section className="landing-how" id="how-it-works">
            <h2>How it works</h2>
            <div className="how-grid">
              {HOW_STEPS.map((step) => (
                <div key={step.num}>
                  <div className={`how-step-num ${step.tone}`}>{step.num}</div>
                  <div className="how-step-title">{step.title}</div>
                  <div className="how-step-desc">{step.desc}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="landing-cta-wrap">
            <div className="landing-cta">
              <div className="landing-cta-blob" aria-hidden="true" />
              <h3>Your friends are already applying.</h3>
              <p>Join a circle, drop a link, get applying.</p>
              <button type="button" onClick={() => onNavigate('signup')}>
                Get started free
              </button>
            </div>
          </section>

          <footer className="landing-footer">
            <div className="landing-logo">
              <DevCareerLogo size={26} />
              <span>© 2026 DevCareer</span>
            </div>
            <div className="landing-footer-links">
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
              <a href="#">Contact</a>
            </div>
          </footer>
        </>
      )}
    </div>
  )
}
