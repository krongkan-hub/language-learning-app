/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import vm from 'node:vm'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { drawCafe } from './scene-cafe'

// The café port against the approved scene (docs/design/pixel/scene-cafe.js):
// both draw on a canvas that writes down every call, and the two lists of
// calls must be the same, for both steam frames and with a speaker in it.

const DESIGN = join(__dirname, '../../../../docs/design/pixel')

type Call = (string | number)[]

function recorder(log: Call[], name: string) {
  const ctx = {
    _fill: '#000000',
    _op: 'source-over',
    set fillStyle(v: string) { this._fill = v },
    get fillStyle() { return this._fill },
    set globalCompositeOperation(v: string) { this._op = v },
    get globalCompositeOperation() { return this._op },
    fillRect(x: number, y: number, w: number, h: number) { log.push([name, 'fill', this._fill, this._op, x, y, w, h]) },
    drawImage(img: { _name: string }, x: number, y: number) { log.push([name, 'draw', img._name, this._op, x, y]) },
  }
  return { _name: name, width: 38, height: 44, getContext: () => ctx, ctx }
}

function original(t: number, withSpeaker: boolean): Call[] {
  const log: Call[] = []
  let n = 0
  const context = vm.createContext({
    Math,
    document: { createElement: () => recorder(log, `tmp${n++}`) },
  })
  vm.runInContext(readFileSync(join(DESIGN, 'kit.js'), 'utf8'), context)
  vm.runInContext(readFileSync(join(DESIGN, 'scene-cafe.js'), 'utf8'), context)
  context.scene = recorder(log, 'scene').ctx
  context.who = withSpeaker ? recorder(log, 'who') : null
  vm.runInContext(`drawCafe(scene, who, ${t})`, context)
  return log
}

function ported(t: number, withSpeaker: boolean): Call[] {
  const log: Call[] = []
  let n = 0
  vi.spyOn(document, 'createElement').mockImplementation(() => recorder(log, `tmp${n++}`) as never)
  const scene = recorder(log, 'scene').ctx as unknown as CanvasRenderingContext2D
  drawCafe(scene, withSpeaker ? (recorder(log, 'who') as unknown as HTMLCanvasElement) : null, t)
  return log
}

afterEach(() => vi.restoreAllMocks())

describe('the café port', () => {
  it.each([[0, true], [1, true], [0, false]])('draws what scene-cafe.js draws (tick %i, speaker %s)', (t, who) => {
    const want = original(t, who)
    expect(want.length).toBeGreaterThan(20000)
    expect(ported(t, who)).toEqual(want)
  })
})
