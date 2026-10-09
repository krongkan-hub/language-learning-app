import type { Expression, Look, Outfit } from './characters'

// A speaker drawn from parts in the Red Pen line style: ink outlines
// (#1B2333), flat fills, a 180x200 bust. Expression is a prop so the face
// can change live — a grin when the learner retypes a correction right.

const INK = '#1B2333'
const STROKE = { stroke: INK, strokeWidth: 2.5, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const }
const SHOULDERS = 'M18 200 C24 150 55 134 90 134 C125 134 156 150 162 200 Z'

function BackHair({ look }: { look: Look }) {
  const fill = look.hairColor
  switch (look.hair) {
    case 'long':
      return <path d="M50 70 C46 120 48 150 56 168 L124 168 C132 150 134 120 130 70 Z" fill={fill} {...STROKE} />
    case 'bob':
      return <path d="M50 70 C46 100 48 118 56 126 L124 126 C132 118 134 100 130 70 Z" fill={fill} {...STROKE} />
    case 'ponytail':
      return <path d="M122 60 C146 70 150 110 138 132 C132 116 130 96 124 82 Z" fill={fill} {...STROKE} />
    default:
      return null
  }
}

function FrontHair({ look }: { look: Look }) {
  const fill = look.hairColor
  switch (look.hair) {
    case 'bald':
      return null
    case 'buzz':
      return <path d="M54 70 C54 46 72 36 90 36 C108 36 126 46 126 70 C116 58 102 54 90 54 C78 54 64 58 54 70 Z" fill={fill} {...STROKE} />
    case 'curly':
      return (
        <path
          d="M50 80 C40 70 46 52 58 50 C58 36 74 28 84 34 C92 24 110 28 112 38 C126 36 136 52 128 62 C138 70 132 84 128 80 C118 64 104 58 90 58 C74 58 60 66 50 80 Z"
          fill={fill} {...STROKE} />
      )
    case 'bun':
      return (
        <g>
          <circle cx="120" cy="34" r="13" fill={fill} {...STROKE} />
          <path d="M52 76 C50 40 74 30 94 31 C118 32 132 50 128 76 C120 60 106 52 88 55 C72 58 60 64 52 76 Z" fill={fill} {...STROKE} />
        </g>
      )
    default:
      return <path d="M52 76 C50 40 74 30 94 31 C118 32 132 50 128 76 C120 60 106 52 88 55 C72 58 60 64 52 76 Z" fill={fill} {...STROKE} />
  }
}

function Brows({ expression }: { expression: Expression }) {
  const d = {
    neutral: ['M68 70 q8 -4 16 0', 'M96 70 q8 -4 16 0'],
    smile: ['M68 68 q8 -5 16 0', 'M96 68 q8 -5 16 0'],
    grin: ['M68 66 q8 -6 16 0', 'M96 66 q8 -6 16 0'],
    calm: ['M68 70 q8 -3 16 0', 'M96 70 q8 -3 16 0'],
    curt: ['M68 70 l16 4', 'M112 70 l-16 4'],
    skeptical: ['M68 72 q8 -2 16 0', 'M96 62 q8 -7 16 -2'],
    harried: ['M68 74 l16 -5', 'M112 74 l-16 -5'],
    concern: ['M68 73 l16 -4', 'M112 73 l-16 -4'],
    surprised: ['M68 62 q8 -7 16 0', 'M96 62 q8 -7 16 0'],
  }[expression]
  return <g fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round">{d.map((p) => <path key={p} d={p} />)}</g>
}

function Eyes({ expression }: { expression: Expression }) {
  if (expression === 'smile' || expression === 'grin') {
    return (
      <g fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round">
        <path d="M70 86 q7 -7 14 0" /><path d="M96 86 q7 -7 14 0" />
      </g>
    )
  }
  if (expression === 'calm') {
    return (
      <g fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round">
        <path d="M70 84 q7 5 14 0" /><path d="M96 84 q7 5 14 0" />
      </g>
    )
  }
  if (expression === 'surprised') {
    return (
      <g>
        <circle cx="77" cy="84" r="6" fill="#FFFFFF" stroke={INK} strokeWidth={2} />
        <circle cx="103" cy="84" r="6" fill="#FFFFFF" stroke={INK} strokeWidth={2} />
        <circle cx="77" cy="84" r="2.6" fill={INK} /><circle cx="103" cy="84" r="2.6" fill={INK} />
      </g>
    )
  }
  const narrow = expression === 'curt' || expression === 'skeptical'
  return (
    <g fill={INK}>
      <ellipse cx="77" cy="85" rx="3.4" ry={narrow ? 2.4 : 4.2} />
      <ellipse cx="103" cy="85" rx="3.4" ry={narrow ? 2.4 : 4.2} />
    </g>
  )
}

function Mouth({ expression }: { expression: Expression }) {
  switch (expression) {
    case 'grin':
      return (
        <g>
          <path d="M74 102 q16 20 32 0 Z" fill="#FFFFFF" {...STROKE} />
          <path d="M82 110 q8 6 16 0" fill="#E0796E" stroke="none" />
        </g>
      )
    case 'smile':
      return <path d="M78 104 q12 12 24 0 Z" fill="#FFFFFF" {...STROKE} />
    case 'calm':
      return <path d="M81 106 q9 6 18 0" fill="none" {...STROKE} />
    case 'curt':
      return <path d="M82 108 h16" fill="none" {...STROKE} />
    case 'skeptical':
      return <path d="M82 109 q8 2 16 -4" fill="none" {...STROKE} />
    case 'harried':
      return <path d="M80 109 q10 -4 20 0" fill="none" {...STROKE} />
    case 'concern':
      return <path d="M81 110 q9 -5 18 0" fill="none" {...STROKE} />
    case 'surprised':
      return <ellipse cx="90" cy="107" rx="6" ry="7" fill="#FFFFFF" {...STROKE} />
    default:
      return <path d="M82 106 q8 4 16 0" fill="none" {...STROKE} />
  }
}

function Body({ outfit, accent }: { outfit: Outfit; accent: string }) {
  switch (outfit) {
    case 'apron':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M60 146 L120 146 L127 200 L53 200 Z" fill="#C8A27A" {...STROKE} />
          <path d="M66 146 L76 134 M114 146 L104 134" fill="none" {...STROKE} />
          <rect x="100" y="160" width="20" height="12" rx="2" fill="#FFFDF6" stroke={INK} strokeWidth={1.5} />
        </g>
      )
    case 'whitecoat':
      return (
        <g>
          <path d={SHOULDERS} fill="#FFFFFF" {...STROKE} />
          <path d="M76 136 L90 170 L104 136 Z" fill={accent} {...STROKE} />
          <path d="M76 136 L70 168 M104 136 L110 168" fill="none" {...STROKE} />
          <path d="M66 150 C60 176 80 186 90 172" fill="none" stroke="#5D6677" strokeWidth={3} strokeLinecap="round" />
          <rect x="112" y="172" width="18" height="10" rx="2" fill="#E2E9F4" stroke={INK} strokeWidth={1.5} />
        </g>
      )
    case 'uniform':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M80 136 L90 150 L100 136" fill="#D9DEE6" {...STROKE} />
          <path d="M34 156 h22 M124 156 h22" stroke="#E9B949" strokeWidth={5} strokeLinecap="round" />
          <path d="M108 164 l6 -4 6 4 v8 l-6 4 -6 -4 Z" fill="#E9B949" stroke={INK} strokeWidth={1.5} />
        </g>
      )
    case 'suit':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M76 136 L90 176 L104 136 Z" fill="#FFFFFF" {...STROKE} />
          <path d="M87 142 L93 142 L95 168 L90 176 L85 168 Z" fill="#C8261B" stroke={INK} strokeWidth={1.5} />
          <path d="M76 136 L84 160 L70 150 M104 136 L96 160 L110 150" fill="none" {...STROKE} />
        </g>
      )
    case 'blazer':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M78 136 L90 160 L102 136 Z" fill="#FFFFFF" {...STROKE} />
          <path d="M78 136 L86 160 L72 152 M102 136 L94 160 L108 152" fill="none" {...STROKE} />
          <rect x="108" y="164" width="24" height="12" rx="2" fill="#FFFDF6" stroke={INK} strokeWidth={1.5} />
          <path d="M112 170 h14" stroke="#5D6677" strokeWidth={1.5} />
        </g>
      )
    case 'vest':
      return (
        <g>
          <path d={SHOULDERS} fill="#FFFFFF" {...STROKE} />
          <path d="M60 148 C64 170 66 186 70 200 L110 200 C114 186 116 170 120 148 L102 140 L90 176 L78 140 Z" fill="#2B2F3A" {...STROKE} />
          <path d="M82 140 l8 5 8 -5 v8 l-8 -5 -8 5 Z" fill={INK} />
        </g>
      )
    case 'overalls':
      return (
        <g>
          <path d={SHOULDERS} fill="#D9DEE6" {...STROKE} />
          <path d="M64 160 L116 160 L120 200 L60 200 Z" fill={accent} {...STROKE} />
          <path d="M68 160 L70 138 M112 160 L110 138" fill="none" stroke={accent} strokeWidth={7} />
          <rect x="82" y="168" width="16" height="12" rx="2" fill="none" {...STROKE} />
        </g>
      )
    case 'ranger':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M80 136 L90 148 L100 136" fill="none" {...STROKE} />
          <rect x="60" y="156" width="20" height="16" rx="2" fill="none" {...STROKE} />
          <rect x="100" y="156" width="20" height="16" rx="2" fill="none" {...STROKE} />
        </g>
      )
    case 'hoodie':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M62 140 C70 158 110 158 118 140" fill="none" {...STROKE} />
          <path d="M84 152 v18 M96 152 v18" fill="none" stroke="#FFFDF6" strokeWidth={2.5} strokeLinecap="round" />
        </g>
      )
    case 'smock':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M78 136 C82 146 98 146 102 136" fill="none" {...STROKE} />
          <circle cx="70" cy="170" r="4" fill="#2A5DB0" /><circle cx="112" cy="160" r="3.5" fill="#C8261B" />
          <circle cx="98" cy="182" r="3" fill="#E9B949" />
        </g>
      )
    case 'chef':
      return (
        <g>
          <path d={SHOULDERS} fill="#FFFFFF" {...STROKE} />
          <path d="M76 136 L104 170 M104 136 L80 168" fill="none" {...STROKE} />
          {[150, 164, 178].map((y) => <circle key={y} cx="100" cy={y} r="2.6" fill={INK} />)}
        </g>
      )
    case 'tailor':
      return (
        <g>
          <path d={SHOULDERS} fill="#FFFFFF" {...STROKE} />
          <path d="M62 148 C66 172 66 188 68 200 L112 200 C114 188 114 172 118 148 L100 140 L90 170 L80 140 Z" fill="#6B4E3D" {...STROKE} />
          <path d="M72 134 C74 160 70 180 66 196 M108 134 C106 160 110 180 114 196" fill="none" stroke="#E9B949" strokeWidth={5} />
        </g>
      )
    case 'cardigan':
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M80 136 L90 150 L100 136 Z" fill="#F3EFE4" {...STROKE} />
          <path d="M90 150 V200" fill="none" {...STROKE} />
          {[164, 180].map((y) => <circle key={y} cx="96" cy={y} r="2.6" fill="#F3EFE4" stroke={INK} strokeWidth={1} />)}
        </g>
      )
    default:
      return (
        <g>
          <path d={SHOULDERS} fill={accent} {...STROKE} />
          <path d="M78 136 C82 146 98 146 102 136" fill="none" {...STROKE} />
        </g>
      )
  }
}

function Hat({ outfit }: { outfit: Outfit }) {
  if (outfit === 'uniform') {
    return (
      <g>
        <path d="M50 52 C56 30 124 30 130 52 Z" fill="#24345A" {...STROKE} />
        <path d="M46 54 H134 L128 62 H52 Z" fill="#1B2333" {...STROKE} />
        <circle cx="90" cy="44" r="5" fill="#E9B949" stroke={INK} strokeWidth={1.5} />
      </g>
    )
  }
  if (outfit === 'ranger') {
    return (
      <g>
        <path d="M30 60 C50 52 130 52 150 60 C130 66 50 66 30 60 Z" fill="#7C6440" {...STROKE} />
        <path d="M58 58 C60 34 120 34 122 58 Z" fill="#A88B57" {...STROKE} />
      </g>
    )
  }
  if (outfit === 'chef') {
    return (
      <path d="M58 52 C44 46 46 22 64 24 C66 8 90 6 96 18 C106 6 132 14 124 30 C138 34 134 52 122 52 Z" fill="#FFFFFF" {...STROKE} />
    )
  }
  return null
}

export function Character({ look, expression = 'neutral', size = 180, title }: {
  look: Look
  expression?: Expression
  size?: number
  title?: string
}) {
  const blush = expression === 'smile' || expression === 'grin'
  return (
    <svg
      width={size}
      height={(size * 200) / 180}
      viewBox="0 0 180 200"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <BackHair look={look} />
      <Body outfit={look.outfit} accent={look.accent} />
      <rect x="80" y="110" width="20" height="28" fill={look.skin} {...STROKE} />
      <ellipse cx="52" cy="84" rx="7" ry="10" fill={look.skin} {...STROKE} />
      <ellipse cx="128" cy="84" rx="7" ry="10" fill={look.skin} {...STROKE} />
      <ellipse cx="90" cy="80" rx="38" ry="44" fill={look.skin} {...STROKE} />
      {look.beard && (
        <path d="M56 92 C58 124 76 128 90 128 C104 128 122 124 124 92 C116 110 102 114 90 114 C78 114 64 110 56 92 Z" fill={look.hairColor} {...STROKE} />
      )}
      {/* Hair before the features: a fringe drawn after them hid the
          raised brow (skeptical) and the sweat drop (harried). */}
      <FrontHair look={look} />
      <Brows expression={expression} />
      <Eyes expression={expression} />
      {blush && (
        <g fill="#F2B0AA">
          <circle cx="68" cy="99" r="6" /><circle cx="112" cy="99" r="6" />
        </g>
      )}
      <Mouth expression={expression} />
      {expression === 'harried' && (
        <path d="M122 58 q5 8 0 12 q-5 -4 0 -12 Z" fill="#9CC3E6" stroke={INK} strokeWidth={1.5} />
      )}
      {look.glasses && (
        <g fill="none" stroke={INK} strokeWidth={2.5}>
          <circle cx="77" cy="85" r="10" /><circle cx="103" cy="85" r="10" /><path d="M87 85 h6" />
        </g>
      )}
      <Hat outfit={look.outfit} />
    </svg>
  )
}
