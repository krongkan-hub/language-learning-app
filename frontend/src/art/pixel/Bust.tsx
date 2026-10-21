import { useLayoutEffect, useMemo, useRef } from 'react'
import { paint, renderKit, type KitSpec, type Pixels } from './render'

/** A spec rendered once per distinct spec: a new object with the same parts is the same bust. */
export function useBust(spec: KitSpec): Pixels {
  const key = JSON.stringify(spec)
  return useMemo(() => renderKit(JSON.parse(key)), [key])
}

/**
 * A pixel character's bust on a canvas, `scale` CSS pixels per art pixel.
 * Decorative unless given a title.
 */
export function Bust({ spec, scale = 3, title, className }:
    { spec: KitSpec; scale?: number; title?: string; className?: string }) {
  const pixels = useBust(spec)
  const ref = useRef<HTMLCanvasElement>(null)
  useLayoutEffect(() => { if (ref.current) paint(ref.current, pixels) }, [pixels])
  return (
    <canvas ref={ref} className={className} width={pixels.w} height={pixels.h}
            style={{ width: pixels.w * scale, height: pixels.h * scale, imageRendering: 'pixelated' }}
            role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true} />
  )
}
