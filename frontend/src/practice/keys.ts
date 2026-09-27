import type { KeyboardEvent } from 'react'

/**
 * Enter that means "send", not Enter that confirms a Japanese IME conversion
 * (こーひー → コーヒー). Chrome reports the latter as keydown Enter with
 * isComposing set; Safari sends keyCode 229. Without this check, picking a
 * kanji sent the half-written turn — on nearly every Japanese message.
 */
export function isSubmitKey(e: KeyboardEvent): boolean {
  return e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229
}
