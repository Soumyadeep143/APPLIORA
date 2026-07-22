import { useState } from 'react'
import { updateNotificationSettings, updateProfileDetails } from './api'
import { BellIcon, GitHubIcon, LinkedInIcon, XIcon } from './Icons'
import './ProfilePage.css'

// One row: platform icon (a live link once a value is saved, otherwise
// just a dimmed glyph) + the URL input itself.
function SocialInputRow({ id, Icon, label, value, placeholder, onChange }) {
  const trimmed = value.trim()
  return (
    <label className="social-input-row">
      {trimmed ? (
        <a
          href={trimmed}
          target="_blank"
          rel="noopener noreferrer"
          className="social-icon-link"
          title={`Open ${label} profile`}
        >
          <Icon size={18} />
        </a>
      ) : (
        <span className="social-icon-link disabled">
          <Icon size={18} />
        </span>
      )}
      <input
        id={id}
        name={id}
        value={value}
        maxLength={300}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

export default function ProfilePage({ user, onLogout, onUpdate }) {
  const [linkedin, setLinkedin] = useState(user.linkedin_url || '')
  const [github, setGithub] = useState(user.github_url || '')
  const [x, setX] = useState(user.x_url || '')
  const [bio, setBio] = useState(user.bio || '')
  const [skills, setSkills] = useState(user.skills || '')
  const [targetRole, setTargetRole] = useState(user.target_role || '')
  const [savingProfile, setSavingProfile] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)
  const [profileError, setProfileError] = useState('')

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [confirmError, setConfirmError] = useState('')

  const [remindersOn, setRemindersOn] = useState(!!user.reminders_opt_in)
  const [remindersSaving, setRemindersSaving] = useState(false)
  const [remindersError, setRemindersError] = useState('')

  // The bell/toggle moved here from the navbar (PRD.md Task 6.16, which
  // also dropped the Reminders popover from every page but Home) — same
  // opt_in_requires_email rule as before, just a different control.
  async function handleToggleReminders() {
    const nextValue = !remindersOn
    setRemindersSaving(true)
    setRemindersError('')
    try {
      const updated = await updateNotificationSettings(user.id, user.email, nextValue)
      onUpdate(updated)
      setRemindersOn(nextValue)
    } catch (err) {
      setRemindersError(err.message)
    } finally {
      setRemindersSaving(false)
    }
  }

  // Every field is independently optional (PRD.md Task 6.14) — a user can
  // save just one of them, and every field stays editable after the first
  // save, not locked in once set.
  async function handleProfileSave(event) {
    event.preventDefault()
    setSavingProfile(true)
    setProfileError('')
    try {
      const updated = await updateProfileDetails(user.id, {
        linkedinUrl: linkedin.trim(),
        githubUrl: github.trim(),
        xUrl: x.trim(),
        bio: bio.trim(),
        skills: skills.trim(),
        targetRole: targetRole.trim(),
      })
      onUpdate(updated)
      setProfileSaved(true)
      setTimeout(() => setProfileSaved(false), 1500)
    } catch (err) {
      setProfileError(err.message)
    } finally {
      setSavingProfile(false)
    }
  }

  function openLogoutConfirm() {
    setConfirmText('')
    setConfirmError('')
    setConfirmOpen(true)
  }

  function handleConfirmSubmit(event) {
    event.preventDefault()
    if (confirmText === 'YES' || confirmText === 'Y') {
      onLogout()
      return
    }
    setConfirmError('Type YES or Y exactly to confirm.')
  }

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-avatar" aria-hidden="true">
          {user.name.trim().charAt(0).toUpperCase()}
        </div>
        <h1>{user.name}</h1>
        <p className="profile-username">@{user.username}</p>
        {user.is_admin && <span className="admin-badge">Admin</span>}

        <dl className="profile-fields">
          <div>
            <dt>Email</dt>
            <dd>{user.email || <span className="muted">Not set</span>}</dd>
          </div>
          <div>
            <dt>Rank points</dt>
            <dd>{user.rank_points}</dd>
          </div>
          <div>
            <dt>Referral code</dt>
            <dd>
              <code>{user.referral_code}</code>
            </dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{user.created_at}</dd>
          </div>
        </dl>

        <div className="reminders-row">
          <span className={`reminders-icon-wrap ${remindersOn ? 'on' : ''}`}>
            <BellIcon size={20} />
            {remindersOn && <span className="reminders-blink-dot" aria-hidden="true" />}
          </span>
          <div className="reminders-copy">
            <p className="reminders-label">Daily reminder emails</p>
            <p className="reminders-sub muted">
              {user.email ? `Sent to ${user.email}` : 'Add an email at signup to enable this'}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={remindersOn}
            aria-label="Toggle daily reminder emails"
            className={`reminders-switch ${remindersOn ? 'on' : ''}`}
            onClick={handleToggleReminders}
            disabled={remindersSaving}
          >
            <span className="reminders-switch-knob" />
          </button>
        </div>
        {remindersError && <p className="auth-error">{remindersError}</p>}

        <form className="social-links" onSubmit={handleProfileSave}>
          <h2 className="social-links-title">About</h2>
          <label className="profile-textfield">
            Bio
            <textarea
              id="profile-bio"
              name="bio"
              rows={3}
              value={bio}
              maxLength={500}
              placeholder="A couple lines about yourself"
              onChange={(event) => setBio(event.target.value)}
            />
          </label>
          <label className="profile-textfield">
            Skills
            <input
              id="profile-skills"
              name="skills"
              value={skills}
              maxLength={300}
              placeholder="e.g. React, Node.js, Python"
              onChange={(event) => setSkills(event.target.value)}
            />
          </label>
          <label className="profile-textfield">
            Targeted role
            <input
              id="profile-target-role"
              name="targetRole"
              value={targetRole}
              maxLength={100}
              placeholder="e.g. Backend Engineer"
              onChange={(event) => setTargetRole(event.target.value)}
            />
          </label>

          <h2 className="social-links-title">Social links</h2>
          <SocialInputRow
            id="profile-linkedin-url"
            Icon={LinkedInIcon}
            label="LinkedIn"
            value={linkedin}
            placeholder="https://www.linkedin.com/in/your-username"
            onChange={setLinkedin}
          />
          <SocialInputRow
            id="profile-github-url"
            Icon={GitHubIcon}
            label="GitHub"
            value={github}
            placeholder="https://github.com/your-username"
            onChange={setGithub}
          />
          <SocialInputRow
            id="profile-x-url"
            Icon={XIcon}
            label="X"
            value={x}
            placeholder="https://x.com/your-username"
            onChange={setX}
          />
          {profileError && <p className="auth-error">{profileError}</p>}
          <button type="submit" className="ghost small" disabled={savingProfile}>
            {savingProfile ? 'Saving…' : profileSaved ? 'Saved ✓' : 'Save profile'}
          </button>
        </form>

        <button type="button" className="ghost small profile-logout" onClick={openLogoutConfirm}>
          Logout
        </button>
      </div>

      {confirmOpen && (
        <div className="logout-modal-overlay" onClick={() => setConfirmOpen(false)}>
          <form
            className="logout-modal"
            onClick={(event) => event.stopPropagation()}
            onSubmit={handleConfirmSubmit}
          >
            <p className="logout-modal-warning">
              Are you sure you want to log out? Type YES or Y to confirm.
            </p>
            <input
              id="logout-confirm-text"
              name="logoutConfirmText"
              autoFocus
              autoComplete="off"
              value={confirmText}
              maxLength={5}
              placeholder="YES or Y"
              onChange={(event) => setConfirmText(event.target.value)}
            />
            {confirmError && <p className="auth-error">{confirmError}</p>}
            <div className="logout-modal-actions">
              <button type="button" className="ghost small" onClick={() => setConfirmOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="profile-logout-confirm">
                Confirm logout
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
