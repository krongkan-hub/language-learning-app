// The shape of GET /api/dashboard (app/db/analytics.py). Kept by hand in step
// with the Python side; dev/tests/test_web.py pins the keys it returns.

export interface Summary {
  sessions: number
  active_days: number
  attempted: number
  completed: number
  completion_rate: number
  taught: number
  learned: number
  due: number
  repeated_classes: number
  streak_days: number
}

export interface Week {
  week: string // ISO date of the week's Monday
  sessions: number
  attempted: number
  completed: number
}

export interface ScenarioRow {
  scenario_name: string
  plays: number
  attempted: number
  completed: number
  completion_rate: number | null
  avg_attempts: number | null
}

export interface Mistake {
  normalized_key: string
  occurrences: number
  example_quoted: string
  example_correction: string
  scenario_name: string
}

export interface Word {
  word: string
  explanation: string
  times_correct: number
  scenario_name: string
}

export interface StageTiming {
  name: string // a span name from app/telemetry.py: turn, judge, actor, coach...
  count: number
  p50_ms: number
  p95_ms: number
}

export interface Dashboard {
  language: string
  summary: Summary
  weekly: Week[]
  scenarios: ScenarioRow[]
  mistakes: Mistake[]
  words: Word[]
  performance: StageTiming[] // last 7 days, all learners
}

export type Language = 'English' | 'Japanese'
