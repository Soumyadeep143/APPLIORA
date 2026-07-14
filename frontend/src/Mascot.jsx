import './mascot.css'

/**
 * Applio — the Appliora assistant mascot.
 *
 * A friendly young professional with fluffy dark hair, expressive brown
 * eyes and a warm smile, wearing a teal hoodie with a minimalist "A"
 * emblem, sitting at a laptop. Pure SVG + CSS keyframes.
 *
 * Moods follow the product storyboard:
 *   idle      — smiling at a glowing job listing on the laptop
 *   waving    — welcoming: found a job? copy the link!
 *   searching — the pasted link turns into floating docs and AI particles
 *   found     — a job card with the extracted details pops up beside the laptop
 *   happy     — glowing checkmark + confetti: shared successfully
 *   sad       — something went wrong
 */
export default function Mascot({ mood = 'idle', message = '' }) {
  return (
    <div className={`mascot mood-${mood}`} role="status" aria-live="polite">
      {message && (
        <div className="mascot-bubble" key={message}>
          {message}
        </div>
      )}
      <svg
        className="mascot-svg"
        viewBox="0 0 150 150"
        width="118"
        height="118"
        aria-label={`Applio the assistant is ${mood}`}
      >
        {/* ground shadow */}
        <ellipse className="m-shadow" cx="75" cy="140" rx="34" ry="5" fill="#12303b" opacity="0.12" />

        <g className="m-body-group">
          {/* ---------- character ---------- */}
          {/* hair back */}
          <circle cx="75" cy="38" r="23" fill="#33283a" />
          <circle cx="56" cy="34" r="8" fill="#33283a" />
          <circle cx="94" cy="34" r="8" fill="#33283a" />
          <circle cx="75" cy="18" r="9" fill="#33283a" />

          {/* neck + head */}
          <rect x="69" y="58" width="12" height="12" rx="4" fill="#f0b98d" />
          <circle cx="75" cy="44" r="21" fill="#f6c39c" />
          {/* ears */}
          <circle cx="54" cy="46" r="4" fill="#f6c39c" />
          <circle cx="96" cy="46" r="4" fill="#f6c39c" />

          {/* fluffy fringe */}
          <path
            d="M54 44 Q52 18 75 16 Q98 18 96 44
               Q93 32 85 33 Q89 25 77 29 Q67 24 66 32
               Q59 28 61 38 Q55 35 54 44 Z"
            fill="#33283a"
          />

          {/* face */}
          <g className="m-face">
            {/* eyebrows */}
            <path className="m-brow" d="M59 37 q5 -3 10 0" fill="none" stroke="#33283a" strokeWidth="2" strokeLinecap="round" />
            <path className="m-brow" d="M81 37 q5 -3 10 0" fill="none" stroke="#33283a" strokeWidth="2" strokeLinecap="round" />

            <g className="m-eyes">
              {/* open brown eyes with highlight */}
              <g className="m-eye">
                <circle cx="64" cy="46" r="3.8" fill="#4a2c17" />
                <circle cx="65.4" cy="44.6" r="1.3" fill="#fff" />
              </g>
              <g className="m-eye">
                <circle cx="86" cy="46" r="3.8" fill="#4a2c17" />
                <circle cx="87.4" cy="44.6" r="1.3" fill="#fff" />
              </g>
              {/* happy ^ ^ */}
              <path className="m-eye-happy" d="M59 47 q5 -6 10 0" fill="none" stroke="#4a2c17" strokeWidth="2.6" strokeLinecap="round" />
              <path className="m-eye-happy" d="M81 47 q5 -6 10 0" fill="none" stroke="#4a2c17" strokeWidth="2.6" strokeLinecap="round" />
              {/* sad closed */}
              <path className="m-eye-sad" d="M59 47 q5 4 10 0" fill="none" stroke="#4a2c17" strokeWidth="2.6" strokeLinecap="round" />
              <path className="m-eye-sad" d="M81 47 q5 4 10 0" fill="none" stroke="#4a2c17" strokeWidth="2.6" strokeLinecap="round" />
            </g>

            {/* blush */}
            <circle className="m-cheek" cx="58" cy="54" r="3.2" fill="#fca5a5" opacity="0.6" />
            <circle className="m-cheek" cx="92" cy="54" r="3.2" fill="#fca5a5" opacity="0.6" />

            {/* mouths */}
            <path className="m-mouth m-mouth-idle" d="M68 56 Q75 62 82 56" fill="none" stroke="#6b3f2a" strokeWidth="2.5" strokeLinecap="round" />
            <path className="m-mouth m-mouth-happy" d="M67 56 A 8 7 0 0 0 83 56 Z" fill="#6b3f2a" />
            <ellipse className="m-mouth m-mouth-o" cx="75" cy="58" rx="3.2" ry="4.2" fill="#6b3f2a" />
            <path className="m-mouth m-mouth-sad" d="M68 61 Q75 55 82 61" fill="none" stroke="#6b3f2a" strokeWidth="2.5" strokeLinecap="round" />
          </g>

          {/* hoodie torso */}
          <path
            d="M48 90 Q48 70 75 70 Q102 70 102 90 L102 120 L48 120 Z"
            fill="#0891b2"
          />
          {/* hood collar */}
          <path d="M61 73 Q75 82 89 73 Q89 66 75 67 Q61 66 61 73 Z" fill="#0e7490" />
          {/* minimalist "A" emblem */}
          <g className="m-emblem" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none">
            <path d="M70 99 L75 85 L80 99" />
            <path d="M72 94 L78 94" />
          </g>

          {/* raised waving arm (welcome) */}
          <g className="m-arm-wave">
            <path d="M53 84 Q40 74 36 60" fill="none" stroke="#0891b2" strokeWidth="9" strokeLinecap="round" />
            <circle cx="35" cy="57" r="5.5" fill="#f6c39c" />
          </g>

          {/* both arms up (success) */}
          <g className="m-arms-up">
            <path d="M53 84 Q38 72 34 56" fill="none" stroke="#0891b2" strokeWidth="9" strokeLinecap="round" />
            <circle cx="33" cy="53" r="5.5" fill="#f6c39c" />
            <path d="M97 84 Q112 72 116 56" fill="none" stroke="#0891b2" strokeWidth="9" strokeLinecap="round" />
            <circle cx="117" cy="53" r="5.5" fill="#f6c39c" />
          </g>

          {/* glowing job listing on the screen (light spills over the lid) */}
          <ellipse className="m-glow" cx="75" cy="106" rx="36" ry="11" fill="#5eead4" opacity="0.4" />

          {/* laptop (back of the lid faces us) */}
          <rect x="42" y="104" width="66" height="30" rx="7" fill="#dcebf0" stroke="#b9d4da" strokeWidth="1.5" />
          <circle cx="75" cy="119" r="3.2" fill="#0891b2" />
          <rect x="37" y="133" width="76" height="5" rx="2.5" fill="#b9d4da" />

          {/* resting hands on the lid */}
          <g className="m-arms-rest">
            <path d="M52 86 Q44 94 47 102" fill="none" stroke="#0891b2" strokeWidth="9" strokeLinecap="round" />
            <circle cx="48" cy="103" r="5" fill="#f6c39c" />
            <path d="M98 86 Q106 94 103 102" fill="none" stroke="#0891b2" strokeWidth="9" strokeLinecap="round" />
            <circle cx="102" cy="103" r="5" fill="#f6c39c" />
          </g>
        </g>

        {/* ---------- floating story elements ---------- */}

        {/* the pasted link becomes documents + AI particles (searching) */}
        <g className="m-docs">
          <g className="m-doc d1">
            <rect x="103" y="62" width="15" height="19" rx="2" fill="#fff" stroke="#b9d4da" strokeWidth="1.2" />
            <line x1="106" y1="68" x2="115" y2="68" stroke="#0891b2" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="106" y1="72" x2="115" y2="72" stroke="#b9d4da" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="106" y1="76" x2="112" y2="76" stroke="#b9d4da" strokeWidth="1.6" strokeLinecap="round" />
          </g>
          <g className="m-doc d2">
            <rect x="118" y="82" width="11" height="14" rx="2" fill="#fff" stroke="#b9d4da" strokeWidth="1.2" />
            <line x1="120.5" y1="87" x2="126.5" y2="87" stroke="#60a5fa" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="120.5" y1="90.5" x2="126.5" y2="90.5" stroke="#b9d4da" strokeWidth="1.4" strokeLinecap="round" />
          </g>
          <circle className="m-particle p1" cx="112" cy="56" r="2.2" fill="#06b6d4" />
          <circle className="m-particle p2" cx="126" cy="70" r="1.8" fill="#60a5fa" />
          <circle className="m-particle p3" cx="120" cy="100" r="2" fill="#5eead4" />
        </g>

        {/* extracted job card pops up (found) */}
        <g className="m-jobcard">
          <rect x="10" y="60" width="38" height="30" rx="4" fill="#fff" stroke="#b9d4da" strokeWidth="1.4" />
          <rect x="15" y="65" width="20" height="3.5" rx="1.75" fill="#0891b2" />
          <rect x="15" y="72" width="28" height="2.8" rx="1.4" fill="#cfe6ea" />
          <rect x="15" y="77" width="22" height="2.8" rx="1.4" fill="#cfe6ea" />
          <circle cx="17.5" cy="85" r="2.4" fill="#60a5fa" />
          <rect x="22" y="83" width="9" height="4" rx="2" fill="#5eead4" />
          <rect x="34" y="83" width="9" height="4" rx="2" fill="#fbbf24" />
        </g>

        {/* glowing checkmark + confetti (happy) */}
        <g className="m-success">
          <circle className="m-check-glow" cx="75" cy="13" r="12" fill="#22c55e" opacity="0.25" />
          <circle cx="75" cy="13" r="8.5" fill="#22c55e" />
          <path d="M70.5 13 l3.2 3.6 6 -7.4" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
          <rect className="m-confetti c1" x="30" y="26" width="4" height="4" rx="1" fill="#06b6d4" />
          <rect className="m-confetti c2" x="114" y="22" width="4" height="4" rx="1" fill="#60a5fa" />
          <rect className="m-confetti c3" x="46" y="12" width="3.5" height="3.5" rx="1" fill="#fbbf24" />
          <rect className="m-confetti c4" x="102" y="10" width="3.5" height="3.5" rx="1" fill="#2dd4bf" />
          <circle className="m-confetti c5" cx="26" cy="50" r="2" fill="#60a5fa" />
          <circle className="m-confetti c6" cx="124" cy="46" r="2" fill="#06b6d4" />
        </g>
      </svg>
    </div>
  )
}
