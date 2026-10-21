import { useEffect, useRef } from 'react'
import { CAFE_H, CAFE_W, drawCafe } from './scene-cafe'
import { paint, type Pixels } from './render'

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

/**
 * The café scene (scene-cafe.js) with the speaker in it, `scale` CSS pixels
 * per art pixel. The steam moves twice a second, unless the learner asked
 * for reduced motion. Decorative: the stage is aria-hidden.
 */
export function Cafe({ who, scale }: { who: Pixels; scale: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const ctx = ref.current?.getContext('2d')
    if (!ctx) return
    const bust = document.createElement('canvas')
    paint(bust, who)
    let tick = 0
    drawCafe(ctx, bust, tick)
    if (reducedMotion()) return
    const t = setInterval(() => drawCafe(ctx, bust, ++tick), 500)
    return () => clearInterval(t)
  }, [who])
  return <canvas ref={ref} width={CAFE_W} height={CAFE_H}
                 style={{ width: CAFE_W * scale, height: CAFE_H * scale, imageRendering: 'pixelated', display: 'block' }} />
}
