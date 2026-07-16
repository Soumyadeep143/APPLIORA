import './LoginPage.css'

export default function LoginPage({
  username,
  setUsername,
  password,
  setPassword,
  loading,
  error,
  toast,
  onSubmit,
  onGoToSignup,
}) {
  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <img src="/favicon.svg" alt="" className="auth-logo" width={40} height={40} />
        <h1>Log in to DevCareer</h1>
        <p className="auth-subtitle">Share jobs with friends — details fetched automatically</p>

        <label>
          Username
          <input
            value={username}
            maxLength={32}
            placeholder="Your username"
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
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
