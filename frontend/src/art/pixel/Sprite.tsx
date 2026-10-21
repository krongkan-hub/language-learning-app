/**
 * A small pixel sprite as SVG: one character a pixel, coloured by `pal`
 * ("." and unknown characters are clear), `scale` CSS pixels per pixel.
 * Decorative unless given a title.
 */
export function Sprite({ rows, pal, scale = 2, title, className }:
    { rows: string[]; pal: Record<string, string>; scale?: number; title?: string; className?: string }) {
  const w = Math.max(...rows.map((r) => r.length)), h = rows.length
  return (
    <svg className={className} width={w * scale} height={h * scale} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges"
         role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      {rows.flatMap((row, y) => [...row].map((ch, x) =>
        pal[ch] ? <rect key={`${x},${y}`} x={x} y={y} width={1} height={1} fill={pal[ch]} /> : null))}
    </svg>
  )
}
