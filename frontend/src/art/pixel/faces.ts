// The six hand-drawn faces, one per mood, at the final 36x42 resolution
// (docs/design/pixel/kit.js HANDFACES, unchanged). Drawn by hand on purpose:
// a procedural face read as a mask. Painted only over skin, origin x9 y10.
//
// b/B brow, l lid, w white, i iris, I iris light, h catch-light, e/s soft
// shade, n/N/H nose, m/M lips, p lower lip, t teeth, o open mouth, c cheek warmth

export type Mood = 'neutral' | 'smile' | 'surprised' | 'confused' | 'annoyed' | 'sad'

export const MOODS: Mood[] = ['neutral', 'smile', 'surprised', 'confused', 'annoyed', 'sad']

export const HANDFACES: Record<Mood, string[]> = {
  neutral: [
    '....................',
    '...Bbbb.....bbbB....',
    '....................',
    '...llll.....llll....',
    '...whiw.....wihw....',
    '...eiie.....eiie....',
    '.........H..........',
    '..c.......n......c..',
    '..cc....NnnN....cc..',
    '....................',
    '.......mmmmmm.......',
    '........pppp........',
    '.........ss.........'],
  smile: [
    '....................',
    '...Bbbb.....bbbB....',
    '....................',
    '...llll.....llll....',
    '...whiw.....wihw....',
    '...ssss.....ssss....',
    '.........H..........',
    '.cc.......n.....cc..',
    '.ccc....NnnN....ccc.',
    '......m......m......',
    '.......mttttm.......',
    '........pppp........',
    '.........ss.........'],
  surprised: [
    '...Bbbb.....bbbB....',
    '....................',
    '...llll.....llll....',
    '...whiw.....wihw....',
    '...wiiw.....wiiw....',
    '...eeee.....eeee....',
    '.........H..........',
    '..c.......n......c..',
    '..cc....NnnN....cc..',
    '........mmmm........',
    '.......moooom.......',
    '........mppm........',
    '.........ss.........'],
  confused: [
    '.............bbbB...',
    '...Bbbb.....b.......',
    '....................',
    '...llll.....llll....',
    '...hiww.....hiww....',
    '...iiee.....iiee....',
    '.........H..........',
    '..c.......n......c..',
    '..cc....NnnN....cc..',
    '....................',
    '.......mm..mmm......',
    '.........mm.........',
    '.........ss.........'],
  annoyed: [
    '....................',
    '...BBb.......bBB....',
    '......b.....b.......',
    '...llll.....llll....',
    '...wiiw.....wiiw....',
    '...ssss.....ssss....',
    '.........H..........',
    '..........n.........',
    '........NnnN........',
    '....................',
    '.......MMMMMM.......',
    '....................',
    '.........ss.........'],
  sad: [
    '.....bB.....Bb......',
    '...Bb.........bB....',
    '....................',
    '...llll.....llll....',
    '...whiw.....wihw....',
    '...eiie.....eiie....',
    '.........H..........',
    '..........n.........',
    '........NnnN........',
    '....................',
    '........mmmm........',
    '.......m....m.......',
    '.........ss.........'],
}
