// Renders the approved kit (docs/design/pixel/kit.js, the original, not the
// port) for the specs in docs/design/pixel/pixel-kit.html, and writes what it
// drew to src/art/pixel/kit.fixtures.json. kit.test.ts holds the TypeScript
// port to these, pixel for pixel. Re-run only if kit.js itself changes:
//   node frontend/scripts/kit-fixtures.mjs
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const here = dirname(fileURLToPath(import.meta.url))
const kit = readFileSync(join(here, '../../docs/design/pixel/kit.js'), 'utf8')

/** A canvas that only records opaque 1x1 fills, which is all kit.js draws. */
function fakeCanvas() {
  const cv = { width: 0, height: 0, px: null }
  const ctx = {
    fillStyle: '#000000',
    clearRect() { cv.px = Array(cv.width * cv.height).fill(null) },
    fillRect(x, y, w, h) {
      if (w !== 1 || h !== 1) throw new Error(`unexpected ${w}x${h} fill`)
      if (x >= 0 && y >= 0 && x < cv.width && y < cv.height) cv.px[y * cv.width + x] = ctx.fillStyle
    },
  }
  cv.getContext = () => ctx
  return cv
}

const ctx = vm.createContext({ Math })
vm.runInContext(kit, ctx)

// pixel-kit.html's specs: the barista in six moods, the twelve example
// characters, and every part on a plain base.
const barista = { head: 'oval', hair: 'ponytail', hairColor: 'auburn', skin: 'a', outfit: 'apron', cloth: '#5a8f6a', accent: '#3d5f47' }
const CAST = {
  barista,
  pharmacist: { head: 'oval', hair: 'bob', hairColor: 'black', skin: 'b', outfit: 'coat', cloth: '#eef0f2', glasses: true },
  officer: { head: 'square', hair: 'cap', hairColor: 'black', skin: 'd', outfit: 'uniform', cloth: '#2f3f6b', mood: 'annoyed', mustache: true },
  student: { head: 'round', hair: 'curly', hairColor: 'brown', skin: 'c', outfit: 'hoodie', cloth: '#c0504d', mood: 'smile' },
  prom: { head: 'oval', hair: 'long', hairColor: 'blond', skin: 'a', outfit: 'gown', cloth: '#7b3f8f', badge: '#f0d9a0', mood: 'surprised' },
  vendor: { head: 'round', hair: 'bun', hairColor: 'black', skin: 'c', outfit: 'apron', cloth: '#e07a3f', accent: '#3a5ea8' },
  office: { head: 'square', hair: 'sidepart', hairColor: 'black', skin: 'b', outfit: 'blazer', cloth: '#4a4e6a', tie: '#3a5ea8', mood: 'confused', stubble: true },
  grandma: { head: 'round', hair: 'bun', hairColor: 'white', skin: 'a', outfit: 'cardigan', cloth: '#a8657e', glasses: true, old: true, mood: 'smile' },
  winDriver: { head: 'square', hair: 'buzz', hairColor: 'black', skin: 'd', outfit: 'winvest', cloth: '#e8742a', badge: '#d8dde3', mood: 'neutral' },
  farmer: { head: 'square', hair: 'strawhat', hatColor: '#d9b56a', hairColor: 'gray', skin: 'c', outfit: 'flannel', cloth: '#a23f3f', beard: true, old: true, mood: 'sad' },
  bartender: { head: 'oval', hair: 'buzz', hairColor: 'ginger', skin: 'a', outfit: 'barvest', cloth: '#26272f', tie: '#8f2a36', beard: true, mood: 'neutral' },
  receptionist: { head: 'oval', hair: 'bob', hairColor: 'black', skin: 'e', outfit: 'blazer', cloth: '#6e3b5a', tie: '#efece4', mood: 'smile' },
}
const specs = { ...CAST }
for (const m of ['neutral', 'smile', 'surprised', 'confused', 'annoyed', 'sad']) specs[`barista-${m}`] = { ...barista, mood: m }
const base = { head: 'oval', hairColor: 'brown', skin: 'b', outfit: 'hoodie', cloth: '#7d84a8', mood: 'neutral' }
for (const h of Object.keys(vm.runInContext('HAIR', ctx))) specs[`hair-${h}`] = { ...base, hair: h }
for (const head of ['oval', 'square', 'round']) specs[`head-${head}`] = { ...base, hair: 'buzz', head }
for (const f of ['mustache', 'beard', 'stubble', 'glasses']) specs[`extra-${f}`] = { ...base, hair: 'buzz', [f]: true }
specs['extra-old'] = { ...base, hair: 'bald', old: true, hairColor: 'gray' }
const OUTFIT_CLOTH = { coat: '#eef0f2', uniform: '#2f3f6b', flannel: '#a23f3f', winvest: '#e8742a', barvest: '#26272f', gown: '#7b3f8f' }
for (const o of ['apron', 'coat', 'uniform', 'blazer', 'flannel', 'hoodie', 'cardigan', 'tank', 'winvest', 'barvest', 'gown']) {
  specs[`outfit-${o}`] = { ...base, hair: 'sidepart', outfit: o, cloth: OUTFIT_CLOTH[o] || '#5f7ec0', ...(o === 'winvest' ? { badge: '#d8dde3' } : {}) }
}
for (const s of Object.keys(vm.runInContext('SKIN', ctx))) specs[`skin-${s}`] = { ...base, hair: 'sidepart', skin: s }
for (const h of Object.keys(vm.runInContext('HAIRC', ctx))) specs[`haircolor-${h}`] = { ...base, hair: 'long', hairColor: h }

// Stored as a palette and one string per row (two base-36 digits a pixel,
// ".." clear), so a failing test can say which pixel moved.
const out = {}
for (const [name, spec] of Object.entries(specs)) {
  const cv = fakeCanvas()
  ctx.cv = cv; ctx.spec = spec
  vm.runInContext('draw(cv, spec)', ctx)
  const palette = [...new Set(cv.px.filter(Boolean))]
  const rows = []
  for (let y = 0; y < cv.height; y++) {
    let r = ''
    for (let x = 0; x < cv.width; x++) {
      const v = cv.px[y * cv.width + x]
      r += v ? palette.indexOf(v).toString(36).padStart(2, '0') : '..'
    }
    rows.push(r)
  }
  out[name] = { spec, w: cv.width, h: cv.height, palette, rows }
}
const file = join(here, '../src/art/pixel/kit.fixtures.json')
writeFileSync(file, JSON.stringify(out, null, 0).replace(/\},"/g, '},\n"') + '\n')
console.log(`${Object.keys(out).length} specs -> ${file}`)
