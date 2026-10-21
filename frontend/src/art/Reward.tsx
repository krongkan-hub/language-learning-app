// The reward for a correction retyped right (#46), drawn for the language
// practised (#62): a 花丸 in a Japanese session, a Gold Star in an English
// one. Which one is copy.ts's call (`reward.icon`), not this file's. The
// sprites are the mockup's (docs/design/pixel/pixel-mockup-v4.html), 8x8.
import { Sprite } from './pixel/Sprite'

const SPRITES = {
  star: ['...o....', '..oyo...', 'ooyyyoo.', 'oyyyyyo.', '.oyyyo..', '.oyoyo..', '.oo.oo..', '........'],
  hanamaru: ['.rr.rr..', 'rrrrrrr.', 'rr.r.rr.', '.r.rr.r.', 'rr...rr.', 'rrrrrrr.', '.rr.rr..', '........'],
  fire: ['...o....', '..oro...', '..orro..', '.oryro..', '.oryyro.', 'oryyyro.', '.oryro..', '..ooo...'],
}
const COLOURS: Record<keyof typeof SPRITES, Record<string, string>> = {
  star: { o: '#a5701a', y: '#f2c14e' },
  hanamaru: { r: '#c0392b' },
  fire: { o: '#7a2a1a', r: '#e8573f', y: '#f2c14e' },
}

export type Icon = keyof typeof SPRITES

/** One of the mockup's 8x8 pixel icons, `size` CSS pixels square. Decorative unless given a title. */
export function PixelIcon({ kind, size = 20, title, className }:
    { kind: Icon; size?: number; title?: string; className?: string }) {
  return <Sprite rows={SPRITES[kind]} pal={COLOURS[kind]} scale={size / 8} title={title} className={className} />
}

export function Reward({ icon, size, title, className }:
    { icon: 'star' | 'hanamaru'; size?: number; title?: string; className?: string }) {
  return <PixelIcon kind={icon} size={size} title={title} className={className} />
}
