// Mirrors the backend's RegisterRequest.valid_password (backend/app/main.py)
// so signup can fail fast client-side instead of round-tripping to the
// server for an obviously invalid password.
export function getPasswordError(password) {
  if (/(.)\1/.test(password)) {
    return "Password can't repeat the same character twice in a row (e.g. 2212) — spaced-out repeats like 2121 are fine."
  }
  if (!/[A-Za-z]/.test(password)) {
    return 'Password must include at least one letter.'
  }
  if (!/\d/.test(password)) {
    return 'Password must include at least one number.'
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return 'Password must include at least one special character.'
  }
  if (password.length < 6) {
    return 'Password must be at least 6 characters.'
  }
  return ''
}
