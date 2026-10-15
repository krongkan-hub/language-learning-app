// The game theme speaks the session language everywhere (#62): one whole
// session per language — HUD, stage, the red-mark card and its retype box,
// the reward pop, Quests, Loot, Boss, Page complete — and not one word of the
// other language in what is shown, in what a screen reader hears (aria-*,
// title, sr-only text, placeholders), or in a `lang` attribute. Extends the
// #67 checks: copy.test.ts (the copy table) and Practice.test.tsx (Today).
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Practice } from './Practice'
import { emit, HEADER, installServer } from './fakeServer'

afterEach(() => vi.unstubAllGlobals())

const CJK = /[぀-ヿ㐀-鿿]/
const LATIN = /[A-Za-z]/

// The served labels (app/i18n.py) the session shows, as /api/strings sends them.
const STRINGS = {
  English: {
    web_skip_task: 'Skip task', web_end: 'End', web_send: 'Send', web_tasks: 'Quests', web_coach: 'Red mark!',
    web_vocabulary: 'Loot', web_input_placeholder: 'Type your reply…', web_again: 'Practice again',
    web_review: 'Review conversation', web_repeat_badge: '🔁 {n}× — you’ve made this mistake before',
  },
  Japanese: {
    web_skip_task: 'タスクをスキップ', web_end: '終了', web_send: '送信', web_tasks: 'クエスト', web_coach: '赤ペン！',
    web_vocabulary: '戦利品', web_input_placeholder: '返事を入力…', web_again: 'もう一度練習する',
    web_review: '会話を見返す', web_repeat_badge: '🔁 {n}回目 — 前にも同じ間違いをしています',
  },
}

const SESSION = {
  English: {
    header: { ...HEADER, art: { scenario: 'Coffee Shop', speaker: 'Barista', mood: 'cheerful' } },
    npc: 'Hi! What can I get you?', task: ['Order a drink', 'Ask the price'], word: ['oat milk', 'milk made from oats'],
    line: 'I want two latte', was: 'two latte', now: 'two lattes', why: 'plural after a number',
  },
  Japanese: {
    header: { ...HEADER, language: 'Japanese', scenario: 'カフェ', place: 'カフェ', speaker: '店員', mood: 'ほがらか',
              art: { scenario: 'Coffee Shop', speaker: 'Barista', mood: 'cheerful' } },
    npc: 'いらっしゃいませ。ご注文は？', task: ['飲み物を注文する', '値段を聞く'], word: ['お冷', '無料の水'],
    line: 'コーヒーを二つをください', was: '二つを', now: '二つ', why: '数のあとに「を」は重ねない',
  },
}

/** Everything a sighted or a screen-reader user gets from the page, as [where, text]. */
function everything(): [string, string][] {
  const out: [string, string][] = [['text', document.body.textContent ?? '']]
  for (const el of document.body.querySelectorAll('*')) {
    for (const a of ['aria-label', 'aria-valuetext', 'title', 'placeholder', 'alt']) {
      const v = el.getAttribute(a)
      if (v) out.push([`${el.tagName.toLowerCase()}[${a}]`, v])
    }
  }
  return out
}

function expectNoLeak(language: 'English' | 'Japanese', moment: string) {
  const other = language === 'English' ? CJK : LATIN
  const leaks = everything().filter(([, v]) => other.test(v))
    .map(([where, v]) => `${moment} ${where}: ${v.match(other === CJK ? /.{0,20}[぀-ヿ㐀-鿿].{0,20}/ : /.{0,20}[A-Za-z].{0,20}/)?.[0]}`)
  expect(leaks).toEqual([])
  const lang = language === 'English' ? 'en' : 'ja'
  expect(document.documentElement.lang).toBe(lang)
  for (const el of document.body.querySelectorAll('[lang]')) expect(el.getAttribute('lang')).toBe(lang)
}

describe.each(['English', 'Japanese'] as const)('a %s session never shows the other language (#62)', (language) => {
  it('in the HUD, the stage, the red-mark card, the reward, the side panel and Page complete', async () => {
    const s = SESSION[language]
    installServer({
      'GET /api/strings': { strings: STRINGS[language] },
      'GET /api/today': { review: [{ was: s.was, fix: s.now, occurrences: 2 }], recent: [], done_today: 1, streak: 3,
                          totals: { tasks_done: 12, fixes: 5, retired: 1 } },
      'POST /api/session': s.header,
      'POST /api/drill/s1': { correct: true, remaining: 0 },
      'POST /api/session/s1/end': { tasks_done: 1, tasks_skipped: 0, words_due: 0 },
    })
    render(<Practice />)
    if (language === 'Japanese') await userEvent.click(screen.getByRole('button', { name: '日本語' }))
    await userEvent.click(await screen.findByRole('button', { name: language === 'English' ? /^Conversation/ : /^会話/ }))
    await waitFor(() => expect(document.getElementById('setup')).toBeNull())

    emit({ type: 'npc', text: s.npc },
         { type: 'tasks', tasks: [{ index: 0, goal: s.task[0], done: true, skipped: false, current: false },
                                  { index: 1, goal: s.task[1], done: false, skipped: false, current: true }] },
         { type: 'vocab', word: s.word[0], explanation: s.word[1] },
         { type: 'state', state: 'awaiting_input' })
    await waitFor(() => expect(document.getElementById('bossBox')?.querySelector('.hp')).not.toBeNull())
    await userEvent.type(screen.getByRole('textbox', { name: STRINGS[language].web_input_placeholder }), `${s.line}{Enter}`)
    emit({ type: 'coach', text: `💡 Feedback:\n- ❌ "${s.was}" → ✅ "${s.now}" (${s.why})`, clean: false,
           repeats: [{ quoted: s.was, occurrences: 2 }] },
         { type: 'drill', target: s.now, remaining: 1 })
    expect(document.getElementById('coachBox')).not.toBeNull()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expectNoLeak(language, 'red-mark card')

    await userEvent.type(document.getElementById('drillInput')!, s.now)
    await userEvent.click(document.querySelector('#drill button')!)
    await waitFor(() => expect(document.querySelector('.reward-pop')).not.toBeNull())
    expectNoLeak(language, 'reward pop')

    emit({ type: 'drill_done' }, { type: 'state', state: 'awaiting_input' })
    await userEvent.click(screen.getByRole('button', { name: STRINGS[language].web_end }))
    await screen.findByRole('dialog', { name: language === 'English' ? 'Page complete' : 'ページ完了' })
    expectNoLeak(language, 'page complete')
  })
})

describe('the reward is named for the language', () => {
  it('English sessions count Gold Stars and Japanese ones 花丸 in the HUD', async () => {
    for (const language of ['English', 'Japanese'] as const) {
      installServer({ 'GET /api/strings': { strings: STRINGS[language] }, 'POST /api/session': SESSION[language].header,
                      'POST /api/session/s1/end': { tasks_done: 1, tasks_skipped: 0, words_due: 0 } })
      const { unmount } = render(<Practice />)
      if (language === 'Japanese') await userEvent.click(screen.getByRole('button', { name: '日本語' }))
      await userEvent.click(await screen.findByRole('button', { name: language === 'English' ? /^Conversation/ : /^会話/ }))
      await waitFor(() => expect(document.getElementById('setup')).toBeNull())
      expect(document.getElementById('hud')).toHaveTextContent(language === 'English' ? '0 Gold Stars this page' : 'このページの花丸 0個')
      unmount()
      vi.unstubAllGlobals()
    }
  })
})
