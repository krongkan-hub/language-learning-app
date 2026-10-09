import type { ReactNode } from 'react'
import type { Goods, SceneSpec, Wall } from './scenes'

// A scenario's backdrop in the Red Pen line style: ink outlines, flat washes,
// a 1000x270 band drawn with preserveAspectRatio "slice" so it fills any
// width. The left third stays quiet — the speaker stands there.

const INK = '#1B2333'
const LINE = { stroke: INK, strokeWidth: 2, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const }

const WALLS: Record<Wall, string> = {
  warm: '#F7EBD6', cool: '#E4ECF4', mint: '#E1EFE8', blush: '#F6E3DE', lavender: '#ECE6F3',
  grey: '#E8E8E3', night: '#2A3350', sky: '#DCEBF5',
}

const WOOD = '#C8A27A'
const WOOD_DARK = '#B08A63'

// ---- small props -----------------------------------------------------------

function Lamp({ x, drop = 50 }: { x: number; drop?: number }) {
  return (
    <g {...LINE} fill="none">
      <path d={`M${x} 0 V${drop}`} />
      <path d={`M${x - 28} ${drop} H${x + 28} L${x + 18} ${drop + 24} H${x - 18} Z`} fill="#FFE27A" />
    </g>
  )
}

function Sign({ x, y, w, text, dark = false }: { x: number; y: number; w: number; text: string; dark?: boolean }) {
  // Space Grotesk caps run ~0.7em plus the letter-spacing; kana and kanji a
  // full em. Measured against "STUDENT SERVICES", which overflowed at 0.62.
  const ems = [...text].reduce((n, ch) => n + (/[\u3000-\u9fff]/.test(ch) ? 1.05 : 0.78), 0)
  const size = Math.min(30, (w - 24) / Math.max(4, ems))
  return (
    <g>
      <rect x={x} y={y} width={w} height={52} rx={6} fill={dark ? '#2C3A35' : '#FFFDF6'} {...LINE} strokeWidth={2.5} />
      <text x={x + w / 2} y={y + 26 + size * 0.36} textAnchor="middle" fontFamily="'Space Grotesk', 'Noto Sans JP', sans-serif"
        fontWeight={700} fontSize={size} letterSpacing={1} fill={dark ? '#F3EFE4' : INK}>{text}</text>
    </g>
  )
}

const PALETTE = ['#F2B0AA', '#CFE0D8', '#FFE27A', '#BFD4E6', '#E8D5B5', '#D9C7E8']

/** One shelf item of a kind, its bottom-left at (x, y). */
function Item({ kind, x, y, i }: { kind: Goods; x: number; y: number; i: number }) {
  const c = PALETTE[i % PALETTE.length]
  switch (kind) {
    case 'cups':
      return <g {...LINE}><rect x={x} y={y - 22} width={20} height={22} rx={3} fill={c} /><path d={`M${x + 20} ${y - 17} q8 0 8 6 q0 6 -8 6`} fill="none" /></g>
    case 'bread':
      return <ellipse cx={x + 16} cy={y - 10} rx={18} ry={10} fill="#D9A866" {...LINE} />
    case 'books':
      return <rect x={x} y={y - 30 + (i % 3) * 3} width={9} height={30 - (i % 3) * 3} fill={c} {...LINE} />
    case 'bottles': case 'wine':
      return <g {...LINE}><rect x={x + 4} y={y - 34} width={6} height={10} fill={kind === 'wine' ? '#7A2E3A' : c} /><rect x={x} y={y - 26} width={14} height={26} rx={3} fill={kind === 'wine' ? '#7A2E3A' : c} /></g>
    case 'flowers':
      return <g {...LINE}><path d={`M${x + 12} ${y - 16} V${y - 34}`} fill="none" /><circle cx={x + 12} cy={y - 38} r={7} fill={c} /><rect x={x + 2} y={y - 18} width={20} height={18} rx={2} fill="#9CC5B0" /></g>
    case 'icecream':
      return <g {...LINE}><rect x={x} y={y - 16} width={28} height={16} rx={2} fill="#FFFDF6" /><path d={`M${x + 2} ${y - 16} q12 -14 24 0`} fill={c} /></g>
    case 'boxes':
      return <g {...LINE}><rect x={x} y={y - 22} width={30} height={22} fill="#D9B98C" /><path d={`M${x + 15} ${y - 22} V${y}`} stroke="#B08A63" /></g>
    case 'clothes': case 'garments':
      return <g {...LINE}><path d={`M${x + 12} ${y - 50} q0 -6 6 -4`} fill="none" /><path d={`M${x} ${y - 40} l12 -8 12 8 v${kind === 'garments' ? 40 : 30} h-24 Z`} fill={kind === 'garments' ? '#EEF2F8' : c} /></g>
    case 'guitars':
      return <g {...LINE}><path d={`M${x + 14} ${y - 70} V${y - 34}`} strokeWidth={4} /><circle cx={x + 14} cy={y - 24} r={11} fill={c} /><circle cx={x + 14} cy={y - 38} r={8} fill={c} /></g>
    case 'tools':
      return <g {...LINE}><path d={`M${x + 4} ${y} V${y - 30}`} strokeWidth={4} /><rect x={x - 4} y={y - 36} width={18} height={8} fill="#8A93A5" /></g>
    case 'screens':
      return <g {...LINE}><rect x={x} y={y - 34} width={50} height={30} rx={2} fill="#1B2333" /><path d={`M${x + 25} ${y - 4} V${y}`} /></g>
    case 'frames':
      return <g {...LINE} fill="none"><circle cx={x + 6} cy={y - 10} r={6} /><circle cx={x + 22} cy={y - 10} r={6} /><path d={`M${x + 12} ${y - 10} h4`} /></g>
    case 'phones':
      return <rect x={x} y={y - 30} width={16} height={30} rx={4} fill={i % 2 ? '#1B2333' : '#D9DEE6'} {...LINE} />
    case 'plants':
      return <g {...LINE}><path d={`M${x + 12} ${y - 16} q-14 -10 -6 -24 q8 8 6 24 q4 -18 14 -20 q2 14 -14 20`} fill="#9CC5B0" /><rect x={x + 2} y={y - 16} width={20} height={16} rx={2} fill="#C8835A" /></g>
    case 'shoes':
      return <path d={`M${x} ${y} v-12 q0 -6 8 -6 q4 8 18 10 q6 2 6 8 Z`} fill={i % 2 ? '#6B4E3D' : '#2B2F3A'} {...LINE} />
    case 'fabric':
      return <rect x={x} y={y - 40} width={14} height={40} rx={4} fill={c} {...LINE} />
    case 'medicine':
      return <g {...LINE}><rect x={x} y={y - 20} width={22} height={20} rx={2} fill="#FFFDF6" /><path d={`M${x + 11} ${y - 15} v10 M${x + 6} ${y - 10} h10`} stroke="#C8261B" strokeWidth={2.5} /></g>
    case 'souvenirs':
      return i % 2
        ? <g {...LINE}><rect x={x} y={y - 18} width={18} height={18} rx={3} fill={c} /><path d={`M${x + 18} ${y - 14} q6 0 6 5 q0 5 -6 5`} fill="none" /></g>
        : <g {...LINE}><path d={`M${x + 4} ${y} V${y - 34}`} /><path d={`M${x + 4} ${y - 34} l18 6 -18 6`} fill={c} /></g>
    case 'cosmetics':
      return <g {...LINE}><rect x={x} y={y - 24 + (i % 2) * 8} width={12} height={24 - (i % 2) * 8} rx={2} fill={c} /><rect x={x + 3} y={y - 30 + (i % 2) * 8} width={6} height={6} fill={INK} /></g>
    case 'produce':
      return <g {...LINE}><rect x={x} y={y - 18} width={40} height={18} fill={WOOD} />{[6, 18, 30].map((dx) => <circle key={dx} cx={x + dx + 2} cy={y - 22} r={7} fill={['#E0796E', '#9CC5B0', '#F2C14E'][(i + dx) % 3]} />)}</g>
    case 'food':
      return <g {...LINE}><ellipse cx={x + 16} cy={y - 6} rx={18} ry={6} fill="#FFFDF6" /><path d={`M${x + 4} ${y - 10} q12 -14 24 0`} fill="#E9A15A" /></g>
    case 'bikes':
      return <g {...LINE} fill="none"><circle cx={x + 10} cy={y - 14} r={13} /><circle cx={x + 48} cy={y - 14} r={13} /><path d={`M${x + 10} ${y - 14} L${x + 26} ${y - 34} H${x + 42} L${x + 48} ${y - 14} M${x + 26} ${y - 34} L${x + 30} ${y - 14}`} stroke="#C8261B" /></g>
    case 'skis':
      return <g {...LINE}><rect x={x} y={y - 70} width={7} height={70} rx={3} fill={c} /><rect x={x + 10} y={y - 70} width={7} height={70} rx={3} fill={c} /></g>
    default:
      return null
  }
}

function Shelf({ x, y, w, goods, rows = 2 }: { x: number; y: number; w: number; goods: Goods; rows?: number }) {
  const step = { books: 11, cups: 32, bread: 40, screens: 60, guitars: 34, bikes: 70, skis: 24, produce: 46, food: 40, boxes: 36, clothes: 30, garments: 30, fabric: 18 }[goods as string] ?? 28
  const shelves: ReactNode[] = []
  for (let r = 0; r < rows; r++) {
    const sy = y + r * 52
    const items: ReactNode[] = []
    for (let i = 0, ix = x + 8; ix + step <= x + w; i++, ix += step) {
      items.push(<Item key={i} kind={goods} x={ix} y={sy} i={i + r * 3} />)
    }
    shelves.push(<g key={r}>{items}<path d={`M${x} ${sy} H${x + w}`} {...LINE} strokeWidth={3} /></g>)
  }
  return <g>{shelves}</g>
}

function Plant({ x, y }: { x: number; y: number }) {
  return (
    <g {...LINE}>
      <path d={`M${x} ${y - 30} C${x - 10} ${y - 80} ${x + 30} ${y - 110} ${x + 40} ${y - 140} C${x + 50} ${y - 105} ${x + 85} ${y - 80} ${x + 75} ${y - 30} Z`} fill="#9CC5B0" />
      <rect x={x + 12} y={y - 34} width={50} height={40} rx={4} fill={WOOD} />
    </g>
  )
}

function Window({ x, y, w, h, night = false, children }: { x: number; y: number; w: number; h: number; night?: boolean; children?: ReactNode }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={night ? '#3D4A6E' : '#CFE4F2'} {...LINE} strokeWidth={3} />
      {children}
      <path d={`M${x + w / 2} ${y} V${y + h} M${x} ${y + h / 2} H${x + w}`} {...LINE} />
    </g>
  )
}

function Skyline({ x, y, w }: { x: number; y: number; w: number }) {
  const blocks = [[0, 40], [24, 62], [52, 30], [72, 74], [104, 46], [128, 58], [156, 36]]
  return (
    <g fill="#A9BCD3" {...LINE} strokeWidth={1.5}>
      {blocks.filter(([dx]) => dx < w - 20).map(([dx, h]) => <rect key={dx} x={x + dx} y={y - h} width={22} height={h} />)}
    </g>
  )
}

function Frame({ x, y, w, h, fill }: { x: number; y: number; w: number; h: number; fill: string }) {
  return (
    <g {...LINE}>
      <rect x={x} y={y} width={w} height={h} fill="#FFFDF6" strokeWidth={3} />
      <rect x={x + 8} y={y + 8} width={w - 16} height={h - 16} fill={fill} />
    </g>
  )
}

function Board({ x, y, w, rows, title }: { x: number; y: number; w: number; rows: string[]; title: string }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={34 + rows.length * 24} rx={4} fill="#1B2333" {...LINE} />
      <text x={x + 14} y={y + 24} fontFamily="'Space Grotesk', 'Noto Sans JP', sans-serif" fontWeight={700} fontSize={16} fill="#FFE27A" letterSpacing={2}>{title}</text>
      {rows.map((r, i) => (
        <text key={r} x={x + 14} y={y + 52 + i * 24} fontFamily="'DM Mono', ui-monospace, monospace" fontSize={15} fill="#F3EFE4">{r}</text>
      ))}
    </g>
  )
}

// ---- templates -------------------------------------------------------------

function CounterScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const night = spec.wall === 'night'
  return (
    <g>
      <Lamp x={520} /><Lamp x={820} drop={40} />
      <Sign x={600} y={60} w={260} text={sign} dark={night} />
      <rect x={430} y={130} width={460} height={8} fill="none" />
      <Shelf x={440} y={190} w={140} goods={spec.goods} rows={1} />
      <Shelf x={880} y={140} w={110} goods={spec.goods} rows={2} />
      <Shelf x={600} y={206} w={240} goods={spec.goods === 'books' || spec.goods === 'guitars' || spec.goods === 'bikes' ? 'none' : spec.goods} rows={1} />
    </g>
  )
}

function DeskScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  return (
    <g>
      <Sign x={560} y={44} w={300} text={sign} />
      <g {...LINE}>
        <circle cx={930} cy={70} r={26} fill="#FFFDF6" /><path d="M930 70 V54 M930 70 L942 78" fill="none" />
      </g>
      {v === 'salon' && <g {...LINE}><rect x={460} y={110} width={70} height={92} rx={34} fill="#E4ECF4" /><rect x={860} y={110} width={70} height={92} rx={34} fill="#E4ECF4" /></g>}
      {(v === 'spa' || v === 'hotel' || v === 'lounge') && <Plant x={880} y={206} />}
      {v === 'gym' && <g {...LINE}><rect x={470} y={150} width={90} height={10} fill="#8A93A5" /><rect x={462} y={136} width={14} height={38} rx={3} fill={INK} /><rect x={554} y={136} width={14} height={38} rx={3} fill={INK} /></g>}
      {(v === 'clinic' || v === 'er' || v === 'vet') && <g {...LINE}><rect x={470} y={110} width={64} height={64} rx={8} fill="#FFFDF6" /><path d="M502 124 v36 M484 142 h36" stroke="#C8261B" strokeWidth={8} /></g>}
      {v === 'police' && <g {...LINE}><path d="M500 110 l26 10 v24 c0 18 -14 28 -26 34 c-12 -6 -26 -16 -26 -34 v-24 Z" fill="#24345A" /><circle cx={500} cy={140} r={8} fill="#E9B949" /></g>}
      {v === 'pool' && <g {...LINE}><rect x={460} y={150} width={110} height={40} rx={4} fill="#9CC3E6" /><path d="M468 166 q10 -8 20 0 q10 8 20 0 q10 -8 20 0 q10 8 20 0" fill="none" stroke="#FFFDF6" strokeWidth={3} /></g>}
      {(v === 'info' || v === 'office' || v === 'bank') && <Frame x={470} y={110} w={90} h={70} fill={v === 'info' ? '#CFE0D8' : '#BFD4E6'} />}
      <g {...LINE}>
        <rect x={560} y={150} width={300} height={60} rx={4} fill="#FFFDF6" strokeWidth={3} />
        <rect x={720} y={116} width={56} height={36} rx={3} fill="#1B2333" /><path d="M748 152 v-6" />
        <path d="M630 146 q10 -14 20 0 Z" fill="#E9B949" /><path d="M626 146 h28" />
      </g>
    </g>
  )
}

function TransitScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  const rows = {
    plane: ['NH 108   TOKYO     ON TIME', 'BA 006   LONDON    BOARDING'],
    train: ['10:42  OSAKA      PLATFORM 4', '10:55  KYOTO      PLATFORM 2'],
    bus: ['14  CITY CENTRE     5 MIN', '27  AIRPORT        12 MIN'],
    storm: ['UA 837   SFO      CANCELLED', 'JL 002   HND      DELAYED'],
    car: ['COMPACT     ECONOMY     SUV', 'PICK-UP  BAY 3'],
    customs: ['NOTHING TO DECLARE  ▸ GREEN', 'GOODS TO DECLARE    ▸ RED'],
  }[v ?? 'plane'] ?? []
  return (
    <g>
      {v === 'storm'
        ? <Window x={440} y={36} w={150} h={110}><path d="M460 70 q20 -20 40 0 q20 -16 34 4 q16 -2 16 14 H460 Z" fill="#8A93A5" /><path d="M480 96 l-6 18 M510 96 l-6 18 M540 96 l-6 18" stroke="#5D7FA6" strokeWidth={2} /></Window>
        : <Window x={440} y={36} w={150} h={110}>{v === 'plane' && <path d="M470 100 l60 -22 l6 6 l-24 14 l10 14 l-6 2 l-14 -10 l-28 10 Z" fill="#FFFDF6" stroke={INK} strokeWidth={1.5} />}</Window>}
      <Board x={620} y={30} w={360} rows={rows} title={sign} />
      <g {...LINE}>
        <rect x={560} y={150} width={320} height={60} rx={4} fill="#D9DEE6" strokeWidth={3} />
        {v !== 'customs' && <rect x={900} y={186} width={90} height={24} fill="#8A93A5" />}
        {v === 'customs' && <path d="M900 150 h80 v60 h-80 Z" fill="#9CC5B0" />}
      </g>
    </g>
  )
}

function OfficeScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  return (
    <g>
      <Window x={440} y={30} w={220} h={150}><Skyline x={450} y={180} w={210} /></Window>
      {v === 'chart' || v === 'startup'
        ? <g {...LINE}><rect x={700} y={40} width={250} height={140} rx={4} fill="#FFFDF6" strokeWidth={3} />
            <path d="M724 160 l40 -30 l36 14 l46 -50 l50 20" fill="none" stroke="#2A5DB0" strokeWidth={3} />
            {v === 'startup' && <g><rect x={724} y={56} width={60} height={34} fill="#FFE27A" /><rect x={796} y={56} width={60} height={34} fill="#F2B0AA" /><rect x={868} y={56} width={60} height={34} fill="#CFE0D8" /></g>}
          </g>
        : <g><Frame x={700} y={40} w={90} h={76} fill="#CFE0D8" /><Sign x={800} y={60} w={190} text={sign} /></g>}
      {(v === 'chart' || v === 'startup') && <Sign x={720} y={190} w={210} text={sign} />}
      {v === 'cowork' && <Plant x={900} y={206} />}
      <g {...LINE}>
        <rect x={560} y={180} width={300} height={14} fill={WOOD} />
        <path d="M640 180 l14 -26 h50 l-6 26" fill="#D9DEE6" />
      </g>
    </g>
  )
}

function MarketScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const night = spec.variant === 'night'
  return (
    <g>
      {night && <g>{Array.from({ length: 14 }, (_, i) => <circle key={i} cx={444 + i * 40} cy={28 + (i % 2) * 8} r={6} fill="#FFE27A" stroke={INK} strokeWidth={1.5} />)}<path d="M440 24 q280 30 560 0" fill="none" {...LINE} /></g>}
      {spec.variant === 'greenhouse'
        ? <g {...LINE} fill="none"><path d="M430 200 V80 L600 30 L770 80 V200" fill="#E1EFE8" /><path d="M515 55 V200 M600 30 V200 M685 55 V200 M430 120 H770" /></g>
        : <g>{Array.from({ length: 8 }, (_, i) => <path key={i} d={`M${440 + i * 70} 60 h70 v34 q-35 16 -70 0 Z`} fill={i % 2 ? '#FFFDF6' : '#C8261B'} {...LINE} />)}
            <path d="M440 94 V206 M1000 94 V206" {...LINE} strokeWidth={4} /></g>}
      <Sign x={600} y={104} w={240} text={sign} dark={night} />
      <Shelf x={460} y={206} w={520} goods={spec.goods} rows={1} />
    </g>
  )
}

function RoadScene({ spec, sign, ja }: { spec: SceneSpec; sign: string; ja?: boolean }) {
  const v = spec.variant
  return (
    <g>
      <path d="M430 180 Q470 130 560 128 Q700 120 760 140 T1000 120 V180 Z" fill="#9CC5B0" {...LINE} />
      <rect x={0} y={180} width={1000} height={90} fill="#6E7682" />
      <path d="M440 226 h60 M560 226 h60 M680 226 h60 M800 226 h60 M920 226 h60" stroke="#FFE27A" strokeWidth={6} />
      {v === 'roadside' && <g {...LINE}><rect x={700} y={120} width={150} height={60} rx={14} fill="#FFFDF6" /><rect x={720} y={110} width={40} height={12} fill="#2A5DB0" /><rect x={760} y={110} width={40} height={12} fill="#C8261B" /><circle cx={730} cy={182} r={14} fill={INK} /><circle cx={820} cy={182} r={14} fill={INK} /></g>}
      {v === 'drive' && <g {...LINE}><rect x={620} y={50} width={300} height={130} fill="#F6E3DE" strokeWidth={3} /><rect x={660} y={90} width={110} height={70} fill="#CFE4F2" /><Sign x={790} y={70} w={120} text={ja ? 'ご注文' : 'ORDER'} /></g>}
      {v === 'car' && <g {...LINE}><path d="M0 0 H1000 V60 Q700 40 400 60 Q200 70 0 50 Z" fill="#2B2F3A" /><circle cx={880} cy={230} r={60} fill="none" stroke={INK} strokeWidth={10} /><rect x={560} y={210} width={110} height={40} rx={8} fill="#1B2333" /></g>}
      <Sign x={440} y={70} w={170} text={sign} />
    </g>
  )
}

function GalleryScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  const night = spec.wall === 'night'
  return (
    <g>
      {[480, 680, 860].map((x) => <g key={x}><path d={`M${x + 40} 0 V18`} {...LINE} /><path d={`M${x + 28} 18 h24 l8 12 h-40 Z`} fill="#FFE27A" {...LINE} /></g>)}
      {v === 'flash'
        ? Array.from({ length: 6 }, (_, i) => <Frame key={i} x={470 + (i % 3) * 120} y={46 + Math.floor(i / 3) * 76} w={96} h={64} fill={PALETTE[i]} />)
        : <g><Frame x={470} y={50} w={150} h={110} fill={v === 'modern' ? '#F2B0AA' : '#CFE0D8'} /><Frame x={660} y={60} w={110} h={90} fill="#BFD4E6" /><Frame x={810} y={46} w={130} h={120} fill={v === 'wedding' ? '#F6E3DE' : '#E8D5B5'} /></g>}
      {v === 'wedding' && <Shelf x={460} y={206} w={500} goods="flowers" rows={1} />}
      {v === 'museum' && <g {...LINE}><rect x={900} y={170} width={60} height={40} fill="#FFFDF6" /><path d="M910 170 q20 -40 40 0" fill="#E8D5B5" /></g>}
      <Sign x={560} y={170} w={220} text={sign} dark={night} />
    </g>
  )
}

function WorkshopScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  return (
    <g>
      <rect x={440} y={36} width={300} height={130} fill="#E8D5B5" {...LINE} />
      {Array.from({ length: 12 }, (_, i) => <circle key={i} cx={460 + (i % 6) * 52} cy={56 + Math.floor(i / 6) * 40} r={2.5} fill={INK} />)}
      <Shelf x={450} y={150} w={280} goods={spec.goods} rows={1} />
      <Sign x={770} y={50} w={200} text={sign} dark={v === 'garage'} />
      {v === 'garage' && <g {...LINE}><circle cx={880} cy={176} r={30} fill="#2B2F3A" /><circle cx={880} cy={176} r={12} fill="#8A93A5" /></g>}
    </g>
  )
}

function HomeScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  if (v === 'hallway') {
    return (
      <g>
        {[460, 700].map((x, i) => <g key={x} {...LINE}><rect x={x} y={40} width={120} height={170} fill={i ? '#C8A27A' : '#8C5A4A'} strokeWidth={3} /><circle cx={x + 100} cy={130} r={5} fill="#E9B949" /><rect x={x + 30} y={60} width={60} height={24} fill="#FFFDF6" /><text x={x + 60} y={78} textAnchor="middle" fontFamily="'Space Grotesk', sans-serif" fontWeight={700} fontSize={16} fill={INK}>{i ? sign : '301'}</text></g>)}
        <Plant x={880} y={210} />
      </g>
    )
  }
  return (
    <g>
      <Window x={460} y={40} w={180} h={130}>{v === 'house' && <path d="M470 160 q40 -40 80 -10 q40 -30 80 0 V170 H470 Z" fill="#9CC5B0" />}</Window>
      <path d="M450 36 q20 70 0 140 M650 36 q-20 70 0 140" fill="#F2B0AA" {...LINE} />
      {(v === 'showroom' || v === 'lived' || v === 'plain') && <g {...LINE}><rect x={700} y={140} width={240} height={50} rx={14} fill="#6B7F5E" /><rect x={690} y={120} width={36} height={70} rx={12} fill="#6B7F5E" /><rect x={914} y={120} width={36} height={70} rx={12} fill="#6B7F5E" /></g>}
      {v === 'showroom' && <Sign x={720} y={50} w={220} text={sign} />}
      {v === 'house' && <Sign x={720} y={60} w={200} text={sign} />}
      {v === 'empty' && <g {...LINE}><rect x={760} y={40} width={110} height={170} fill="#E8D5B5" strokeWidth={3} /><circle cx={850} cy={130} r={5} fill="#E9B949" /><Sign x={880} y={60} w={100} text={sign} /></g>}
      {v === 'lived' && <g {...LINE}><path d="M840 40 q10 30 -4 60" stroke="#5D7FA6" strokeWidth={3} fill="none" /><Sign x={720} y={50} w={160} text={sign} /></g>}
    </g>
  )
}

function OutdoorsScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  const snow = v === 'snow'
  return (
    <g>
      <circle cx={900} cy={50} r={26} fill="#FFE27A" {...LINE} />
      <path d="M430 180 L520 70 L620 150 L740 50 L900 180 Z" fill={snow ? '#FFFFFF' : v === 'beach' ? '#F3E3C0' : '#9CC5B0'} {...LINE} />
      
      {v === 'vineyard' && Array.from({ length: 5 }, (_, i) => <path key={i} d={`M${560 + i * 70} 180 q-20 -30 0 -60 q20 30 0 60`} fill="#6B7F5E" {...LINE} />)}
      {(v === 'forest' || snow) && (snow ? [470] : [460, 820, 930]).map((x) => <path key={x} d={`M${x} 190 l26 -70 l26 70 Z`} fill={snow ? '#6B7F5E' : '#4F7A5A'} {...LINE} />)}
      <g {...LINE}><path d="M560 206 V120 L650 84 L740 120 V206" fill={WOOD} /><rect x={600} y={140} width={100} height={66} fill="#FFFDF6" /></g>
      <Sign x={540} y={88} w={220} text={sign} />
      {spec.goods !== 'none' && <Shelf x={760} y={206} w={230} goods={spec.goods} rows={1} />}
    </g>
  )
}

function BoxOfficeScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const v = spec.variant
  return (
    <g>
      {v === 'park' && <g {...LINE} fill="none"><circle cx={940} cy={130} r={46} /><path d="M940 84 V176 M894 130 H986" /></g>}
      <rect x={480} y={30} width={440} height={64} rx={8} fill="#2C3A35" {...LINE} strokeWidth={3} />
      {Array.from({ length: 20 }, (_, i) => <circle key={i} cx={492 + i * 22} cy={30} r={5} fill="#FFE27A" stroke={INK} strokeWidth={1} />)}
      <text x={700} y={74} textAnchor="middle" fontFamily="'Space Grotesk', 'Noto Sans JP', sans-serif" fontWeight={700} fontSize={30} fill="#FFE27A" letterSpacing={3}>{sign}</text>
      <g {...LINE}>
        <rect x={560} y={110} width={280} height={100} fill="#F6E3DE" strokeWidth={3} />
        <rect x={600} y={126} width={200} height={60} rx={30} fill="#CFE4F2" />
      </g>
      {v === 'bowling' && <g {...LINE}>{[880, 910, 940].map((x) => <path key={x} d={`M${x} 206 q-8 -20 0 -40 q-4 -10 0 -16 q4 6 0 16 q8 20 0 40 Z`} fill="#FFFDF6" />)}</g>}
      {(v === 'cinema' || v === 'concert') && <g><Frame x={870} y={110} w={90} h={96} fill="#F2B0AA" /><Frame x={420} y={110} w={90} h={96} fill="#BFD4E6" /></g>}
      {v === 'karaoke' && <g {...LINE}><rect x={890} y={120} width={18} height={50} rx={9} fill="#8A93A5" /><path d="M899 170 V206" /></g>}
      {v === 'escape' && <g {...LINE}><rect x={880} y={110} width={80} height={100} fill="#6B4E3D" /><circle cx={920} cy={160} r={12} fill="#E9B949" /><rect x={916} y={160} width={8} height={18} fill={INK} /></g>}
    </g>
  )
}

function HarborScene({ spec, sign }: { spec: SceneSpec; sign: string }) {
  const port = spec.variant === 'port'
  return (
    <g>
      <path d="M440 170 q20 -8 40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0" fill="none" stroke="#FFFDF6" strokeWidth={3} />
      {port
        ? <g {...LINE}><path d="M760 150 V30 H900 M780 30 V60" fill="none" strokeWidth={4} /><rect x={560} y={110} width={60} height={40} fill="#C8261B" /><rect x={620} y={110} width={60} height={40} fill="#2A5DB0" /><rect x={590} y={70} width={60} height={40} fill="#E9B949" /></g>
        : <g {...LINE}><path d="M600 150 l20 -40 h200 l20 40 Z" fill="#FFFDF6" /><rect x={660} y={80} width={110} height={30} fill="#BFD4E6" /><rect x={700} y={56} width={20} height={24} fill="#C8261B" /></g>}
      <Sign x={440} y={60} w={200} text={sign} />
    </g>
  )
}

function KitchenScene({ sign }: { spec: SceneSpec; sign: string }) {
  return (
    <g>
      {Array.from({ length: 30 }, (_, i) => <rect key={i} x={440 + (i % 10) * 54} y={30 + Math.floor(i / 10) * 40} width={54} height={40} fill="#FFFDF6" {...LINE} strokeWidth={1} />)}
      <Sign x={560} y={60} w={260} text={sign} />
      <g {...LINE}>
        <rect x={460} y={150} width={60} height={34} rx={4} fill="#8A93A5" /><path d="M450 150 h80" />
        <rect x={860} y={146} width={70} height={40} rx={6} fill="#C8261B" /><path d="M852 150 h86" />
      </g>
    </g>
  )
}

const TEMPLATES: Record<SceneSpec['template'], (p: { spec: SceneSpec; sign: string; ja?: boolean }) => ReactNode> = {
  counter: CounterScene, desk: DeskScene, transit: TransitScene, office: OfficeScene,
  market: MarketScene, road: RoadScene, gallery: GalleryScene, workshop: WorkshopScene,
  home: HomeScene, outdoors: OutdoorsScene, boxoffice: BoxOfficeScene, harbor: HarborScene,
  kitchen: KitchenScene,
}

/** The floor line each template stands on, so the full-width strip behind
 *  the props meets the counter the props draw. */
interface Floor { y: number; color: string; edge: string; band?: { y: number; color: string } }

function floorOf(spec: SceneSpec): Floor {
  const v = spec.variant
  switch (spec.template) {
    case 'desk': return { y: 210, color: '#E8D5B5', edge: '#D9C2A0' }
    case 'transit': return { y: 210, color: '#CFD6E0', edge: '#B9C2CF' }
    case 'office': return { y: 248, color: '#D9DEE6', edge: '#C5CCD6' }
    case 'road': return { y: 180, color: '#6E7682', edge: '#6E7682' }
    case 'gallery': return spec.wall === 'night'
      ? { y: 226, color: '#3B3F55', edge: '#2E3247' } : { y: 226, color: '#E8E8E3', edge: '#D6D6CF' }
    case 'workshop': return v === 'garage'
      ? { y: 206, color: '#8A93A5', edge: '#6E7682' } : { y: 206, color: WOOD, edge: WOOD_DARK }
    case 'home': return { y: v === 'hallway' ? 210 : 206, color: '#D9C2A0', edge: '#C9B08C' }
    case 'outdoors': return v === 'snow'
      ? { y: 206, color: '#EEF2F8', edge: '#DCE3EE' }
      : { y: 206, color: '#B9C79A', edge: '#A6B585', band: v === 'beach' ? { y: 150, color: '#9CC3E6' } : undefined }
    case 'boxoffice': return { y: 210, color: '#3B3F55', edge: '#2E3247' }
    case 'harbor': return { y: 220, color: WOOD, edge: WOOD_DARK, band: { y: 150, color: '#9CC3E6' } }
    case 'kitchen': return { y: 186, color: '#D9DEE6', edge: '#C5CCD6' }
    default: return { y: 206, color: WOOD, edge: WOOD_DARK }
  }
}

// The props live in x 420..1000 of the drawing and are pinned to the right
// edge at a fixed aspect: a single viewBox with "slice" cropped the right
// side off ("REPA…", "HARDW…") whenever the column was narrower than wide.
// The wall and the floor are plain full-width layers behind them.
const PROPS_X = 420
const PROPS_W = 1000 - PROPS_X

export function Scene({ spec, language = 'English', height = 270 }: {
  spec: SceneSpec
  language?: string
  height?: number
}) {
  const Template = TEMPLATES[spec.template]
  const sign = language === 'Japanese' ? spec.sign[1] : spec.sign[0]
  const floor = floorOf(spec)
  // One ink line for the floor, scaled with the drawing: the props no longer
  // draw a counter of their own, which met this layer 2px off (review #52).
  const k = height / 270
  const pct = (y: number) => `${(y / 270) * 100}%`
  return (
    <div aria-hidden="true" style={{ position: 'relative', height, overflow: 'hidden', background: WALLS[spec.wall] }}>
      {floor.band && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: pct(floor.band.y), height: `${((floor.y - floor.band.y) / 270) * 100}%`,
          background: floor.band.color, borderTop: `${2 * k}px solid ${INK}` }} />
      )}
      <div style={{ position: 'absolute', left: 0, right: 0, top: `calc(${pct(floor.y)} - ${1.5 * k}px)`, bottom: 0,
        background: floor.color, borderTop: `${3 * k}px solid ${INK}`, boxShadow: `inset 0 ${12 * k}px 0 ${floor.edge}` }} />
      <svg viewBox={`${PROPS_X} 0 ${PROPS_W} 270`} preserveAspectRatio="xMaxYMax meet"
        style={{ position: 'absolute', right: 0, top: 0, height: '100%', width: (PROPS_W / 270) * height }}>
        <Template spec={spec} sign={sign} ja={language === 'Japanese'} />
      </svg>
    </div>
  )
}
