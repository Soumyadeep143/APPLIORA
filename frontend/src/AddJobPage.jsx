import './AddJobPage.css'

const URL_INPUT_RE = /^https?:\/\/\S+$/i

export default function AddJobPage({
  user,
  linkInput,
  setLinkInput,
  fetching,
  onFetch,
  draft,
  draftNotes,
  draftConfidence,
  updateDraft,
  onShare,
  saving,
  onCancelDraft,
}) {
  return (
    <section className="share-box" id="share-a-job">
      <h2>Share a job</h2>
      <form className="link-row" onSubmit={onFetch}>
        <textarea
          id="addjob-link-input"
          name="linkInput"
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
        <form className="draft" onSubmit={onShare}>
          {draftNotes.map((note) => (
            <p key={note} className="note">
              {note}
            </p>
          ))}
          <div className="field-grid">
            <label>
              Job link {!draft.apply_email.trim() && '*'}
              <input
                id="addjob-url"
                name="url"
                type="url"
                value={draft.url}
                maxLength={2000}
                placeholder="https://… the real apply link"
                onChange={updateDraft('url')}
              />
            </label>
            <label>
              Apply email {!draft.url.trim() && '*'}
              <input
                id="addjob-apply-email"
                name="applyEmail"
                type="email"
                value={draft.apply_email}
                maxLength={200}
                placeholder="recruiter@company.com"
                onChange={updateDraft('apply_email')}
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
                id="addjob-title"
                name="title"
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
                id="addjob-company"
                name="company"
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
                id="addjob-deadline"
                name="deadline"
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
                id="addjob-location"
                name="location"
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
              id="addjob-description"
              name="description"
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
            <button type="button" className="ghost" onClick={onCancelDraft}>
              Cancel
            </button>
            <span className="sharing-as">
              {user ? (
                <>
                  Sharing as <strong>{user.name}</strong>
                </>
              ) : (
                'Log in before sharing so friends know who shared this'
              )}
            </span>
          </div>
        </form>
      )}
    </section>
  )
}
