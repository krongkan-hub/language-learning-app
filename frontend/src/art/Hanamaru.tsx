// 花丸: the flower-circle a Japanese teacher draws on work done right. The
// app's reward (#46): a correction retyped right earns one.
const PETALS = 'M84 50 A13 13 0 0 1 74.04 74.04 A13 13 0 0 1 50 84 A13 13 0 0 1 25.96 74.04 A13 13 0 0 1 16 50 A13 13 0 0 1 25.96 25.96 A13 13 0 0 1 50 16 A13 13 0 0 1 74.04 25.96 A13 13 0 0 1 84 50 Z'
const SPIRAL = 'M50 50 m-4 0 a4 4 0 1 1 8 0 a8 8 0 1 1 -16 0 a12 12 0 1 1 24 0 a16 16 0 1 1 -32 0 a20 20 0 1 1 40 0'

export function Hanamaru({ size = 48, title, className }: { size?: number; title?: string; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 100 100"
         role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      <g transform="rotate(-8 50 50)" fill="none" stroke="var(--pen)" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round">
        <path d={PETALS} />
        <path d={SPIRAL} />
      </g>
    </svg>
  )
}
