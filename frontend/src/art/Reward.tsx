// The reward for a correction retyped right (#46), drawn for the language
// practised (#62): a 花丸 in a Japanese session, a Gold Star in an English
// one. Which one is copy.ts's call (`reward.icon`), not this file's.
import { Hanamaru } from './Hanamaru'

const STAR = 'M50 8 L61.8 35.6 L92 38.2 L69 58 L76 87.6 L50 72 L24 87.6 L31 58 L8 38.2 L38.2 35.6 Z'

export function GoldStar({ size = 48, title, className }: { size?: number; title?: string; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 100 100"
         role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      <path d={STAR} fill="var(--gold)" stroke="var(--shadow)" strokeWidth={5} strokeLinejoin="round" />
      <path d="M50 22 L57 38" stroke="#fff6c8" strokeWidth={5} strokeLinecap="round" />
    </svg>
  )
}

export function Reward({ icon, size, title, className }:
    { icon: 'star' | 'hanamaru'; size?: number; title?: string; className?: string }) {
  return icon === 'star'
    ? <GoldStar size={size} title={title} className={className} />
    : <Hanamaru size={size} title={title} className={className} />
}
