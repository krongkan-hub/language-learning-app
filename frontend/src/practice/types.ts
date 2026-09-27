// The practice screen's side of the web API (app/web/routes.py) and of the
// server-sent events a session emits (app/web/turns.py). Kept by hand in step
// with the Python side.

export type Language = 'English' | 'Japanese'
export type Mode = 'scenario' | 'explain'
/** Every visible label, from /api/strings (app/i18n.py), in the language being studied. */
export type Strings = Record<string, string>

export interface Task {
  index: number
  goal: string
  done: boolean
  skipped: boolean
  current: boolean
}

/** How far the scenario is from its next rung, and the words still waiting. */
export interface Progress {
  next_rank?: string | null
  plays_needed?: number
  pct_needed?: number
}

/** The header fields both POST /api/session and GET /api/session/{sid} return. */
export interface SessionHeader {
  session: string
  language: Language
  mode: Mode
  scenario: string
  place: string
  speaker: string
  mood: string
  total_tasks: number
  retried_note: string
}

/** GET /api/session/{sid}: everything a reloaded page needs. */
export interface Snapshot extends SessionHeader {
  state: string
  tasks: Task[]
  messages: { role: 'user' | 'assistant'; content: string }[]
  words: string[]
  drill: string[]
  tasks_done: number
  tasks_missed: number
  progress?: Progress
  words_due?: number
}

export interface EndResult {
  tasks_done: number
  tasks_skipped: number
  progress?: Progress
  words_due?: number
}

export interface Repeat {
  quoted: string
  occurrences: number
}

export type ServerEvent =
  | { type: 'sentence'; text: string }
  | { type: 'npc'; text: string }
  | { type: 'vocab'; word: string; explanation: string; repeat?: boolean }
  | { type: 'vocab_used'; words: { word: string; count: number }[] }
  | { type: 'coach'; text: string; clean: boolean; repeats?: Repeat[] }
  | { type: 'tasks'; tasks: Task[] }
  | { type: 'drill'; target: string; remaining: number }
  | { type: 'drill_done' }
  | { type: 'task_result'; done: boolean; moved_on?: boolean; attempts: number; max_attempts?: number;
      goal?: string; strategy?: string; hint?: string }
  | { type: 'stage'; name: string }
  | { type: 'finished'; tasks_done: number; tasks_total: number; tasks_missed: number;
      progress?: Progress; words_due?: number }
  | { type: 'error'; message?: string; detail?: string }
  | { type: 'state'; state: string }
  | { type: 'closed' }

export interface ScenarioCard {
  name: string
  display_name: string
  place: string
  mastery_label: string
  plays: number
}

export interface StatRow {
  scenario_name?: string
  topic_name?: string
  plays?: number
  best_pct?: number
  mastery?: string
}

export interface Stats {
  overall?: { sessions_played?: number; tasks_completed?: number; tasks_attempted?: number;
              overall_completion_rate?: number }
  vocab?: { learned_words?: number; due_words?: number }
  scenarios?: Record<string, StatRow>
  topics?: Record<string, StatRow>
  mistakes?: { example_quoted?: string; example_correction?: string; occurrences: number }[]
}
