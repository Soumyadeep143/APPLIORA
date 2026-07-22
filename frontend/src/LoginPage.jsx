import Mascot from './Mascot'
import './LoginPage.css'

function mascotForLogin({ error, succeeded, toast, username, password }) {
  if (error) return { mood: 'sad', message: error }
  // `toast` covers "just arrived here after signing up" for free — that's
  // exactly when App.jsx's toast is "Successfully signed up! Log in to
  // continue.", so no separate signup-success wiring is needed here.
  if (succeeded || toast) return { mood: 'happy', message: toast || 'Successfully logged in!' }
  if (username || password) return { mood: 'idle', message: '' }
  return { mood: 'waving', message: "Welcome back! Log in to see what your circle's sharing." }
}

export default function LoginPage({
  username,
  setUsername,
  password,
  setPassword,
  loading,
  error,
  toast,
  succeeded,
  onSubmit,
  onGoToSignup,
}) {
  const { mood, message } = mascotForLogin({ error, succeeded, toast, username, password })

  return (
    <div className="auth-page">
      <Mascot mood={mood} message={message} />
      <form className="auth-card" onSubmit={onSubmit}>
        <img src="/favicon.svg" alt="" className="auth-logo" width={40} height={40} />
        <h1>Log in to DevCareer</h1>
        <p className="auth-subtitle">Share jobs with friends — details fetched automatically</p>

        <label>
          Username
          <input
            id="login-username"
            name="username"
            autoComplete="username"
            value={username}
            maxLength={32}
            placeholder="Your username"
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            maxLength={200}
            placeholder="Password"
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {toast && <p className="auth-success">{toast}</p>}
        {error && <p className="auth-error">{error}</p>}

        <button
          type="submit"
          className="auth-submit"
          disabled={loading || !username.trim() || !password.trim()}
        >
          {loading ? 'Signing in…' : 'Log in'}
        </button>
        <button type="button" className="auth-switch" onClick={onGoToSignup}>
          New here? Sign up free
        </button>
      </form>
    </div>
  )
}
