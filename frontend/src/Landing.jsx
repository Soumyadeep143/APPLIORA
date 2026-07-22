import { useEffect, useRef, useState } from 'react'
import { getStats, listJobs, updateNotificationSettings } from './api'
import { deadlineInfo } from './dateUtils'
import CountUp from './CountUp'
import TextType from './TextType'
import Dock from './Dock'
import BorderGlow from './BorderGlow'
import Mascot from './Mascot'
import {
  AwardIcon,
  BellIcon,
  BriefcaseIcon,
  CloseIcon,
  CrownIcon,
  HelpCircleIcon,
  HomeIcon,
  MenuIcon,
  PlusCircleIcon,
  ShieldIcon,
  TrendingUpIcon,
  UserIcon,
} from './Icons'
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

// Rotated by the hero's TextType — each on its own two-line beat like the
// original static "Climb faster, / with your crew." headline, but calling
// out the other concrete things the product actually does for a user.
const HERO_TAGLINES = [
  'Climb faster,\nwith your crew.',
  'Job hunting,\nsolved together.',
  'Never miss a deadline,\nagain.',
  'Share one link,\napply as a crew.',
]

// Landing hero headline numbers — order here drives which /api/stats field
// feeds each CountUp.
const STAT_ITEMS = [
  { key: 'jobs_shared', label: 'jobs shared' },
  { key: 'friend_circles', label: 'friend circles' },
  { key: 'companies_posted', label: 'companies posted' },
]

// Mascot (Applio) reactions as the user scrolls through Home's sections —
// keyed by the section's existing id (see the JSX further down), checked
// via IntersectionObserver in the Landing component itself.
const SECTION_MASCOT = {
  trending: { mood: 'found', message: 'Fresh jobs from your circle, hot off the press 👀' },
  'how-it-works': { mood: 'waving', message: "Here's the whole flow, in three steps." },
  'get-started': { mood: 'happy', message: "Ready? Your crew's waiting 🚀" },
}

// Precedence (top wins): actively typing in the hero search beats the
// one-time arrival greeting beats whichever tracked section is in view
// beats Applio's resting idle state. Greeting/typing outrank the
// scroll-tracked section deliberately — on a short viewport Trending
// already sits partly in view before any scrolling happens at all, and
// without this order it would swallow both the arrival greeting and the
// search reaction the instant the page loads.
function computeHomeMood({ activeSection, query, homeGreeting }) {
  if (query.trim()) return { mood: 'searching', message: 'Let’s find that for you…' }
  if (homeGreeting) {
    return { mood: 'waving', message: "Hi, I'm Applio! Glad you're here — let's find your next role." }
  }
  if (activeSection && SECTION_MASCOT[activeSection]) return SECTION_MASCOT[activeSection]
  return { mood: 'idle', message: '' }
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

// Moved here from App.jsx (PRD.md Task 6.10) — Landing's header is the one
// persistent nav shown on every page, so this popover belongs in the
// navbar rather than a page-level header that only some views rendered.
function NotificationSettings({ user, onUpdate }) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState(user.email || '')
  const [optIn, setOptIn] = useState(!!user.reminders_opt_in)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  // Click anywhere outside the panel closes it — it was previously only
  // dismissible via the toggle button, so it could sit open indefinitely
  // on top of the page.
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
      <button
        type="button"
        className="ghost small nav-icon-link"
        onClick={() => setOpen((value) => !value)}
      >
        <BellIcon size={16} />
        <span className="nav-label">Reminders</span>
      </button>
      {open && (
        <form className="notif-panel" onSubmit={handleSave}>
          <label>
            Email
            <input
              id="notif-email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              maxLength={200}
              placeholder="you@example.com"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="notif-checkbox">
            <input
              id="notif-opt-in"
              name="optIn"
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

// activeView drives which page is showing (PRD.md Task 6.4: Browse Jobs /
// Add Job / Log in-Sign up are distinct pages, not scroll positions on one
// long page). This header is the one persistent nav across all of them.
export default function Landing({ activeView, onNavigate, onSearch, user, setUser }) {
  const [query, setQuery] = useState('')
  const [trendingJobs, setTrendingJobs] = useState(null)
  // Zeros (not null) so CountUp always has a numeric `to` to animate from
  // on first render — real counts swap in once /api/stats resolves.
  const [stats, setStats] = useState({ jobs_shared: 0, friend_circles: 0, companies_posted: 0 })
  // Phone-width nav drawer (PRD.md Task 6.15) — .landing-links/.landing-
  // identity collapse into this below ~720px (landing.css); tablet widths
  // get a compact icon-only row instead (no drawer needed there).
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  // Mascot (Applio) reactions on Home — which scroll-tracked section (if
  // any) is currently in view, and whether the one-time arrival greeting
  // is still showing. See computeHomeMood above for how these combine.
  const [activeSection, setActiveSection] = useState(null)
  const [homeGreeting, setHomeGreeting] = useState(false)

  useEffect(() => {
    setMobileNavOpen(false)
  }, [activeView])

  useEffect(() => {
    if (activeView !== 'home') return undefined
    setHomeGreeting(true)
    const timer = setTimeout(() => setHomeGreeting(false), 4000)
    return () => clearTimeout(timer)
  }, [activeView])

  useEffect(() => {
    if (activeView !== 'home') {
      setActiveSection(null)
      return undefined
    }
    const ids = Object.keys(SECTION_MASCOT)

    // Whichever tracked section's own vertical center sits closest to the
    // viewport's center "wins" — tried an IntersectionObserver ratio
    // comparison first, but these sections are short enough that two of
    // the three are often simultaneously 100%-visible at once on a normal
    // laptop viewport, so "highest ratio" is a coin-flip tie in exactly
    // the cases that matter. Distance-to-center has no such tie.
    let rafId = null
    function updateActiveSection() {
      rafId = null

      // The last tracked section (the final CTA) is followed only by a
      // short footer, so on a short page there's often not enough room
      // below it to ever scroll it to true center — at max scroll its
      // midpoint can still sit well below center, losing to the section
      // above it. Scrolled to the bottom unambiguously means "looking at
      // the last section", so short-circuit straight to it.
      const atBottom =
        window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4
      if (atBottom) {
        setActiveSection(ids[ids.length - 1])
        return
      }

      const viewportMid = window.innerHeight / 2
      let closestId = null
      let closestDistance = Infinity
      for (const id of ids) {
        const el = document.getElementById(id)
        if (!el) continue
        const rect = el.getBoundingClientRect()
        if (rect.bottom <= 0 || rect.top >= window.innerHeight) continue // fully off-screen
        const distance = Math.abs(rect.top + rect.height / 2 - viewportMid)
        if (distance < closestDistance) {
          closestDistance = distance
          closestId = id
        }
      }
      setActiveSection(closestId)
    }
    function scheduleUpdate() {
      if (rafId === null) rafId = requestAnimationFrame(updateActiveSection)
    }

    updateActiveSection()
    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)
    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId)
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
    }
  }, [activeView])

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

  useEffect(() => {
    let cancelled = false
    getStats()
      .then((data) => {
        if (!cancelled) setStats(data)
      })
      .catch(() => {
        // Marketing page shouldn't break if the API hiccups — same
        // "empty over broken" principle as the trending fetch above.
      })
    return () => {
      cancelled = true
    }
  }, [])

  function handleSearch(event) {
    event.preventDefault()
    onSearch(query.trim())
  }

  // Every nav item gets a real icon, not emoji (PRD.md Task 6.12/6.13) —
  // Icon is a component (from './Icons'), rendered before the label.
  // Profile passes label={null} for an icon-only link (no visible text).
  function navLink(view, Icon, label) {
    const classes = ['nav-icon-link']
    if (activeView === view) classes.push('active')
    if (!label) classes.push('icon-only')
    return (
      <a
        href="#"
        className={classes.join(' ')}
        aria-label={label || view}
        title={label || view}
        onClick={(event) => {
          event.preventDefault()
          onNavigate(view)
          setMobileNavOpen(false)
        }}
      >
        <Icon size={16} />
        {label && <span className="nav-label">{label}</span>}
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

  function homeSectionLink(id, Icon, label) {
    return (
      <a
        href="#"
        className="nav-icon-link"
        onClick={(event) => {
          event.preventDefault()
          goToHomeSection(id)
          setMobileNavOpen(false)
        }}
      >
        <Icon size={16} />
        <span className="nav-label">{label}</span>
      </a>
    )
  }

  // Phone-only bottom tab bar (landing.css hides it above 720px — same
  // breakpoint the drawer nav switches at). A handful of the drawer's
  // links, not all of them: this is a quick-access dock, not a full nav
  // replacement.
  const mobileDockItems = [
    {
      icon: <HomeIcon size={20} />,
      label: 'Home',
      onClick: () => onNavigate('home'),
      className: activeView === 'home' ? 'active' : '',
    },
    {
      icon: <BriefcaseIcon size={20} />,
      label: 'Browse',
      onClick: () => onNavigate('board'),
      className: activeView === 'board' ? 'active' : '',
    },
    {
      icon: <PlusCircleIcon size={20} />,
      label: 'Add Job',
      onClick: () => onNavigate('share'),
      className: activeView === 'share' ? 'active' : '',
    },
    {
      icon: <AwardIcon size={20} />,
      label: 'Leaderboard',
      onClick: () => onNavigate('leaderboard'),
      className: activeView === 'leaderboard' ? 'active' : '',
    },
    user
      ? {
          icon: <UserIcon size={20} />,
          label: 'Profile',
          onClick: () => onNavigate('profile'),
          className: activeView === 'profile' ? 'active' : '',
        }
      : {
          icon: <UserIcon size={20} />,
          label: 'Log in',
          onClick: () => onNavigate('login'),
          className: activeView === 'login' ? 'active' : '',
        },
  ]

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-logo" role="button" tabIndex={0} onClick={() => onNavigate('home')}>
          <DevCareerLogo />
          <span>DevCareer</span>
        </div>
        <button
          type="button"
          className="landing-menu-toggle"
          aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileNavOpen}
          onClick={() => setMobileNavOpen((value) => !value)}
        >
          {mobileNavOpen ? <CloseIcon size={22} /> : <MenuIcon size={22} />}
        </button>
        <nav className={`landing-nav ${mobileNavOpen ? 'open' : ''}`}>
          <div className="landing-links">
            {navLink('home', HomeIcon, 'Home')}
            {navLink('board', BriefcaseIcon, 'Browse Jobs')}
            {navLink('share', PlusCircleIcon, 'Add Job')}
            {navLink('leaderboard', AwardIcon, 'Leaderboard')}
            {homeSectionLink('how-it-works', HelpCircleIcon, 'How it works')}
            {homeSectionLink('trending', TrendingUpIcon, 'Trending')}
            {user?.is_admin && navLink('admin', ShieldIcon, 'Admin')}
            {user?.is_superadmin && navLink('superadmin', CrownIcon, 'Super Admin')}
          </div>
          {user ? (
            <div className="landing-identity">
              {/* Reminders popover only on Home (PRD.md Task 6.16) — every
                  other page dropped it from the navbar in favor of the
                  toggle on Profile itself. */}
              {activeView === 'home' && <NotificationSettings user={user} onUpdate={setUser} />}
              {navLink('profile', UserIcon, null)}
            </div>
          ) : (
            <>
              <a
                href="#"
                className="landing-loginlink"
                onClick={(event) => {
                  event.preventDefault()
                  onNavigate('login')
                  setMobileNavOpen(false)
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
                  setMobileNavOpen(false)
                }}
              >
                Sign up free
              </a>
            </>
          )}
        </nav>
      </header>

      <div className="landing-mobile-dock-wrap">
        <Dock
          items={mobileDockItems}
          panelHeight={58}
          baseItemSize={44}
          magnification={56}
          distance={100}
          className="landing-mobile-dock"
        />
      </div>

      {activeView === 'home' && (
        <>
          <Mascot {...computeHomeMood({ activeSection, query, homeGreeting })} />

          <section className="landing-hero">
            <div className="landing-blob landing-blob-a" aria-hidden="true" />
            <div className="landing-blob landing-blob-b" aria-hidden="true" />

            <div className="landing-badge">Built for job-hunting crews</div>
            <TextType
              as="h1"
              text={HERO_TAGLINES}
              typingSpeed={65}
              deletingSpeed={35}
              pauseDuration={2200}
              initialDelay={150}
              cursorCharacter="|"
              cursorClassName="landing-hero-cursor"
            />
            <p>
              Paste a job link, DevCareer fills in the title, company and deadline — your circle
              reacts, comments and applies together.
            </p>

            <div className="landing-search">
              <BorderGlow
                className="landing-search-glow"
                backgroundColor="#ffffff"
                borderRadius={14}
                glowRadius={26}
                glowIntensity={1.3}
                coneSpread={30}
                edgeSensitivity={20}
                glowColor="21 100 59"
                colors={['#ff7a30', '#4a90d9', '#1e5aa8']}
              >
                <form onSubmit={handleSearch}>
                  <input
                    id="landing-hero-search"
                    name="heroSearch"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search Frontend, Backend, DevOps, ML…"
                    aria-label="Search jobs"
                  />
                  <button type="submit">Search</button>
                </form>
              </BorderGlow>
            </div>

            <div className="landing-stats">
              {STAT_ITEMS.map(({ key, label }) => (
                <div key={key}>
                  <div className="landing-stat-num">
                    <CountUp to={stats[key]} separator="," duration={1.2} />
                  </div>
                  <div className="landing-stat-label">{label}</div>
                </div>
              ))}
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

          <section className="landing-cta-wrap" id="get-started">
            <div className="landing-cta">
              <div className="landing-cta-blob" aria-hidden="true" />
              <h3>Your friends are already applying.</h3>
              <p>Join a circle, drop a link, get applying.</p>
              <button type="button" onClick={() => onNavigate(user ? 'board' : 'signup')}>
                Get started free
              </button>
            </div>
          </section>

          
        </>
      )}
    </div>
  )
}
