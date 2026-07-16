import './SignupPage.css'

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
  onSubmit,
  onGoToLogin,
}) {
  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <img src="/favicon.svg" alt="" className="auth-logo" width={40} height={40} />
        <h1>Join DevCareer</h1>
        <p className="auth-subtitle">Create your account — sign up first, then log in.</p>

        <label>
          Username
          <input
            value={username}
            maxLength={32}
            placeholder="How you'll log in (letters, numbers, no spaces)"
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Name
          <input
            value={name}
            maxLength={80}
            placeholder="Your display name"
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={email}
            maxLength={200}
            placeholder="you@example.com"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            maxLength={200}
            placeholder="Password (6+ characters)"
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <label>
          Referral code (optional)
          <input
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
