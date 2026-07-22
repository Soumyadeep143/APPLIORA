import Mascot from './Mascot'
import './SignupPage.css'

function mascotForSignup({ error, succeeded, username, name, email, password }) {
  if (error) return { mood: 'sad', message: error }
  if (succeeded) return { mood: 'happy', message: "Woohoo, you're in! Taking you to log in…" }
  if (username || name || email || password) return { mood: 'idle', message: '' }
  return { mood: 'waving', message: "Hi, I'm Applio! Let's get your crew set up 🎉" }
}

export default function SignupPage({
  username,
  setUsername,
  name,
  setName,
  email,
  setEmail,
  password,
  setPassword,
  referralCode,
  setReferralCode,
  loading,
  error,
  succeeded,
  onSubmit,
  onGoToLogin,
}) {
  const { mood, message } = mascotForSignup({ error, succeeded, username, name, email, password })

  return (
    <div className="auth-page">
      <Mascot mood={mood} message={message} />
      <form className="auth-card" onSubmit={onSubmit}>
        <img src="/favicon.svg" alt="" className="auth-logo" width={40} height={40} />
        <h1>Join DevCareer</h1>
        <p className="auth-subtitle">Create your account — sign up first, then log in.</p>

        <label>
          Username
          <input
            id="signup-username"
            name="username"
            autoComplete="username"
            value={username}
            maxLength={32}
            placeholder="How you'll log in (letters, numbers, no spaces)"
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Name
          <input
            id="signup-name"
            name="name"
            autoComplete="name"
            value={name}
            maxLength={80}
            placeholder="Your display name"
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Email
          <input
            id="signup-email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            maxLength={200}
            placeholder="you@example.com"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            id="signup-password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            maxLength={200}
            placeholder="Password (6+ characters)"
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <p className="auth-hint">
          Letters, numbers and a special character, no back-to-back repeats
          (2212 isn't allowed, but 2121 is fine).
        </p>
        <label>
          Referral code (optional)
          <input
            id="signup-referral-code"
            name="referralCode"
            autoComplete="off"
            value={referralCode}
            maxLength={20}
            placeholder="Got one from a friend?"
            onChange={(event) => setReferralCode(event.target.value)}
          />
        </label>

        {error && <p className="auth-error">{error}</p>}

        <button
          type="submit"
          className="auth-submit"
          disabled={loading || !username.trim() || !name.trim() || !email.trim() || !password.trim()}
        >
          {loading ? 'Creating…' : 'Sign up free'}
        </button>
        <button type="button" className="auth-switch" onClick={onGoToLogin}>
          Have an account? Log in
        </button>
      </form>
    </div>
  )
}
