// Small inline SVG icons — no emoji, no external icon font/CDN (this app
// is fully self-contained). All use `currentColor` so they inherit
// whatever text color their surrounding element has (nav link, active
// state, etc.) rather than carrying their own fixed color.

// Shared wrapper for the feather-icons-style line icons below (Home
// through User) — same stroke weight/caps throughout so the whole navbar
// reads as one icon set rather than a mix of styles.
function StrokeIcon({ size, children }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export function HomeIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 0 0 1 1h3m10-11l2 2m-2-2v10a1 1 0 0 1-1 1h-3m-6 0a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1m-6 0h6" />
    </StrokeIcon>
  )
}

export function BriefcaseIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </StrokeIcon>
  )
}

export function PlusCircleIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="16" />
      <line x1="8" y1="12" x2="16" y2="12" />
    </StrokeIcon>
  )
}

export function HelpCircleIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </StrokeIcon>
  )
}

export function TrendingUpIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </StrokeIcon>
  )
}

export function ShieldIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </StrokeIcon>
  )
}

export function BellIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </StrokeIcon>
  )
}

export function AwardIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <circle cx="12" cy="8" r="7" />
      <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
    </StrokeIcon>
  )
}

export function UserIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </StrokeIcon>
  )
}

// Mobile nav hamburger toggle (PRD.md Task 6.15) — Menu/Close, not the
// social XIcon further down (that's the "X" brand mark, unrelated).
export function MenuIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </StrokeIcon>
  )
}

export function CloseIcon({ size = 18 }) {
  return (
    <StrokeIcon size={size}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </StrokeIcon>
  )
}

// Solid (not stroke) — a zigzag crown reads poorly as a thin outline at
// nav-icon size, so this one's filled like the brand icons below.
export function CrownIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M3 17l1.5-8L9 13l3-7 3 7 4.5-4L21 17H3z" />
      <rect x="3" y="18" width="18" height="2" rx="1" />
    </svg>
  )
}

export function LinkedInIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45z" />
    </svg>
  )
}

export function GitHubIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.16-.02-2.11-3.2.7-3.88-1.36-3.88-1.36-.53-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.71.08-.71 1.17.08 1.78 1.2 1.78 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.23-1.28-5.23-5.67 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 2.9-.39c.98 0 1.97.13 2.9.39 2.2-1.49 3.17-1.18 3.17-1.18.64 1.59.24 2.76.12 3.05.74.8 1.19 1.83 1.19 3.08 0 4.4-2.69 5.38-5.25 5.66.42.36.78 1.08.78 2.18 0 1.57-.01 2.84-.01 3.23 0 .31.2.66.79.55A11.5 11.5 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5z"
      />
    </svg>
  )
}

export function XIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18.9 2H22l-7.6 8.7L23 22h-6.8l-5.3-6.9L4.8 22H2l8.1-9.3L1.5 2h7l4.8 6.3L18.9 2zm-1.2 18h1.9L7.4 4H5.4l12.3 16z" />
    </svg>
  )
}
