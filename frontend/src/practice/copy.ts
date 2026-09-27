// The few visible lines that are not in app/i18n.py: the landing page's
// loading screen, connection notices, toasts and the summary sentence. They
// used to be inline `lang === 'Japanese' ? … : …` ternaries scattered through
// the page; one table per language keeps them in one place. Every label that
// IS in i18n.py comes from /api/strings instead (see useStrings in Practice).
import type { Language } from './types'

const EN = {
  htmlLang: 'en',
  boot: {
    preparing: ['Preparing your scenario', 'Translating the objectives…'],
    greeting: ['Setting the scene', 'The model is warming up — this is the slow part.'],
  } as Record<string, [string, string]>,
  stage: { judging: 'Checking your answer…', replying: 'Writing a reply…', coaching: 'Reviewing your grammar…' } as Record<string, string>,
  thinking: 'thinking…',
  reconnecting: 'Connection lost — reconnecting…',
  ended: 'This session has ended. Reload to start a new one.',
  resumed: 'Picked your session back up.',
  finishFirst: 'Finish the correction first.',
  skipped: 'Task skipped',
  taskDone: '✓ Task complete',
  newWord: (w: string) => `📖 New word: ${w}`,
  couldntSend: "Couldn't send that",
  natural: '✓ Sounds natural',
  levelUp: 'Level up',
  left: (n: number) => `${n} left`,
  doneLine: (done: number, missed: number) => `${done} tasks completed · ${missed} missed`,
  rank: (r: string) => r,
  playsTo: (n: number, rank: string) => `${n} more play${n > 1 ? 's' : ''} to ${rank}`,
  pctTo: (p: number, rank: string) => `${p}% better to reach ${rank}`,
  wordsDue: (n: number) => `${n} word${n > 1 ? 's' : ''} waiting to be practised`,
  sep: ' · ',
  landing: (played: number, tasks: number, words: number) => `${played} sessions · ${tasks} tasks · ${words} words`,
  kpi: { sessions: 'Sessions', tasks: 'Tasks', completion: 'Completion', words: 'Words' },
  fixes: 'Corrections this session',
}

type Copy = typeof EN

const JA: Copy = {
  htmlLang: 'ja',
  boot: {
    preparing: ['シナリオを準備しています', '目標を翻訳しています…'],
    greeting: ['シナリオを用意しています', 'モデルの起動中です。最初だけ時間がかかります。'],
  },
  stage: { judging: '回答を確認しています…', replying: '返事を書いています…', coaching: '文法を見ています…' },
  thinking: '考えています…',
  reconnecting: '接続が切れました。再接続しています…',
  ended: 'セッションが終了しました。ページを再読み込みしてください。',
  resumed: 'セッションを再開しました。',
  finishFirst: '先に訂正を入力してください。',
  skipped: 'タスクをスキップしました',
  taskDone: '✓ タスク達成！',
  newWord: (w) => `📖 新しい単語: ${w}`,
  couldntSend: '送信できませんでした',
  natural: '✓ 自然です',
  levelUp: 'レベルアップ',
  left: (n) => `あと${n}件`,
  doneLine: (done, missed) => `達成 ${done}件・未達成 ${missed}件`,
  rank: (r) => ({ experienced: '経験者', mastered: 'マスター' } as Record<string, string>)[r] ?? r,
  playsTo: (n, rank) => `あと${n}回プレイで「${rank}」に`,
  pctTo: (p, rank) => `ベストスコアをあと${p}%上げると「${rank}」に`,
  wordsDue: (n) => `復習待ちの単語 ${n}語`,
  sep: ' ・ ',
  landing: (played, tasks, words) => `${played}回練習・タスク${tasks}件達成・単語${words}語`,
  kpi: { sessions: 'セッション', tasks: 'タスク', completion: '達成率', words: '単語' },
  fixes: '今回の訂正',
}

export const copyFor = (lang: Language): Copy => (lang === 'Japanese' ? JA : EN)
