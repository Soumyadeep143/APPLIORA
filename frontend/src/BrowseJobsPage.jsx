import { useState } from 'react'
import { deleteComment, listComments, postComment } from './api'
import { deadlineInfo } from './dateUtils'
import './BrowseJobsPage.css'

// Fixed set, not a free-form picker — mirrors ALLOWED_REACTIONS in
// backend/app/main.py (Task 3.3).
const REACTION_EMOJI = ['👍', '🔥', '🎯', '🎉']

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

function ReactionRow({ job, user, onReact }) {
  const counts = {}
  const mine = new Set()
  for (const reaction of job.reactions) {
    counts[reaction.emoji] = (counts[reaction.emoji] || 0) + 1
    if (user && reaction.user_id === user.id) mine.add(reaction.emoji)
  }

  return (
    <div className="reaction-row">
      {REACTION_EMOJI.map((emoji) => {
        const count = counts[emoji] || 0
        return (
          <button
            key={emoji}
            type="button"
            className={`reaction-btn ${mine.has(emoji) ? 'active' : ''}`}
            disabled={!user}
            title={user ? undefined : 'Log in to react'}
            aria-label={mine.has(emoji) ? `Remove ${emoji} reaction` : `React with ${emoji}`}
            aria-pressed={mine.has(emoji)}
            onClick={() => onReact(job, emoji)}
          >
            <span aria-hidden="true">{emoji}</span>
            {count > 0 && <span className="reaction-count">{count}</span>}
          </button>
        )
      })}
    </div>
  )
}

function CommentThread({ job, user, onCommentCountChange }) {
  const [open, setOpen] = useState(false)
  const [comments, setComments] = useState(null) // null = not loaded yet
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState('')
  const [posting, setPosting] = useState(false)
  const [threadError, setThreadError] = useState('')

  async function toggleOpen() {
    const next = !open
    setOpen(next)
    if (!next || comments !== null) return
    setLoading(true)
    try {
      setComments(await listComments(job.id))
    } catch (err) {
      setThreadError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handlePostComment(event) {
    event.preventDefault()
    if (!text.trim() || !user) return
    setPosting(true)
    setThreadError('')
    try {
      const comment = await postComment(job.id, user.id, text.trim())
      setComments((current) => [...(current || []), comment])
      setText('')
      onCommentCountChange(job.id, 1)
    } catch (err) {
      setThreadError(err.message)
    } finally {
      setPosting(false)
    }
  }

  async function handleDeleteComment(comment) {
    try {
      await deleteComment(job.id, comment.id, user.id)
      setComments((current) => current.filter((item) => item.id !== comment.id))
      onCommentCountChange(job.id, -1)
    } catch (err) {
      setThreadError(err.message)
    }
  }

  return (
    <div className="comment-thread">
      <button type="button" className="link-btn comment-toggle" onClick={toggleOpen}>
        💬 {job.comment_count > 0 ? `${job.comment_count} comment${job.comment_count === 1 ? '' : 's'}` : 'Comment'}
      </button>
      {open && (
        <div className="comment-panel">
          {loading && <p className="muted">Loading comments…</p>}
          {threadError && <p className="comment-error">{threadError}</p>}
          {comments && comments.length === 0 && !loading && (
            <p className="muted">No comments yet — be the first!</p>
          )}
          {comments &&
            comments.map((comment) => (
              <div className="comment" key={comment.id}>
                <span className="avatar" aria-hidden="true">
                  {comment.user_name.charAt(0).toUpperCase()}
                </span>
                <div className="comment-body">
                  <p className="comment-meta">
                    <strong>{comment.user_name}</strong>{' '}
                    <span className="muted">{timeAgo(comment.created_at)}</span>
                  </p>
                  <p className="comment-text">{comment.body}</p>
                </div>
                {user && comment.user_id === user.id && (
                  <button
                    type="button"
                    className="icon-btn small"
                    aria-label="Delete comment"
                    onClick={() => handleDeleteComment(comment)}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          {user ? (
            <form className="comment-form" onSubmit={handlePostComment}>
              <input
                placeholder="Add a comment…"
                value={text}
                maxLength={1000}
                onChange={(event) => setText(event.target.value)}
              />
              <button type="submit" disabled={posting || !text.trim()}>
                {posting ? 'Posting…' : 'Post'}
              </button>
            </form>
          ) : (
            <p className="muted">Log in to comment.</p>
          )}
        </div>
      )}
    </div>
  )
}

function EmailApplyChip({ email, subject }) {
  const [copied, setCopied] = useState(false)
  const mailtoHref = `mailto:${email}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(email)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard permission denied — the mailto: link below still works */
    }
  }

  return (
    <span className="apply-email-chip">
      <a href={mailtoHref} title="Open your email client">
        ✉️ {email}
      </a>
      <button type="button" className="icon-btn small" onClick={handleCopy} aria-label="Copy apply email">
        {copied ? 'Copied ✓' : 'Copy'}
      </button>
    </span>
  )
}

function JobCard({ job, index, user, onDelete, onReact, onCommentCountChange }) {
  const [expanded, setExpanded] = useState(false)
  const deadline = deadlineInfo(job.deadline)
  const longDescription = job.description.length > 260
  // Staggered entrance — capped so a long feed doesn't leave late cards
  // waiting a visibly long time to appear.
  const entranceDelay = `${Math.min((index ?? 0) * 60, 480)}ms`
  const titleHref = job.url || (job.apply_email ? `mailto:${job.apply_email}` : '')

  return (
    <article className="job-card" style={{ animationDelay: entranceDelay }}>
      <div className="job-card-head">
        <div>
          <h3 className="job-title">
            {titleHref ? (
              <a href={titleHref} target="_blank" rel="noreferrer">
                {job.title}
              </a>
            ) : (
              job.title
            )}
          </h3>
          <div className="job-meta">
            {job.company && <span className="company">{job.company}</span>}
            {job.location && <span className="dot-sep">{job.location}</span>}
            {job.source && <span className="dot-sep source">{job.source}</span>}
          </div>
        </div>
        {user?.is_admin && (
          <button
            className="icon-btn"
            aria-label="Remove this job"
            title="Remove this job (admin)"
            onClick={() => onDelete(job)}
          >
            ✕
          </button>
        )}
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

      <div className="job-card-social">
        <ReactionRow job={job} user={user} onReact={onReact} />
        <CommentThread job={job} user={user} onCommentCountChange={onCommentCountChange} />
      </div>

      <footer className="job-card-foot">
        <span className="shared-by">
          <span className="avatar" aria-hidden="true">
            {(job.shared_by || 'A').trim().charAt(0).toUpperCase()}
          </span>
          Shared by <strong>{job.shared_by}</strong> · {timeAgo(job.created_at)}
        </span>
        <span className="job-card-actions">
          {job.apply_email && (
            <EmailApplyChip email={job.apply_email} subject={job.apply_email_subject} />
          )}
          {job.url && (
            <a className="apply-btn" href={job.url} target="_blank" rel="noreferrer">
              Apply ↗
            </a>
          )}
        </span>
      </footer>
    </article>
  )
}

export default function BrowseJobsPage({
  jobs,
  loading,
  search,
  onSearchChange,
  user,
  onDelete,
  onReact,
  onCommentCountChange,
}) {
  return (
    <section className="feed" id="job-board">
      <div className="feed-head">
        <h2>
          Shared jobs {jobs.length > 0 && <span className="count">{jobs.length}</span>}
        </h2>
        <input
          className="search-input"
          placeholder="Search title, company, friend…"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
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
        {jobs.map((job, index) => (
          <JobCard
            key={job.id}
            job={job}
            index={index}
            user={user}
            onDelete={onDelete}
            onReact={onReact}
            onCommentCountChange={onCommentCountChange}
          />
        ))}
      </div>
    </section>
  )
}
