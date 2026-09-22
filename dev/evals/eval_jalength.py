"""Does sentence LENGTH hide a Japanese error from the coach? OPEN-48's open half.

In English the same error scored 27/27 alone in a short sentence and 12/27
unchanged inside a long one, 15 of the misses called "Perfectly natural!".
Clause splitting took that to 18/27 — for English only, because Japanese was
never measured and inheriting the English boundaries would be shipping a guess.
This is that measurement.

Every pair is one error written twice: the SHORT sentence is exactly an
`eval_jarecall.py` probe, and the LONG sentence carries that same erroneous
phrase unchanged inside a sentence a learner would plausibly type. No
situation line in either arm, so length is the only variable. The two
arms go through `call_coach`, the path a real turn takes, so a splitter
added to `_grammar_units` is measured here and nowhere else.

Read this WITH the clean arm, never alone: six long, fully correct
sentences. A long-arm gain that costs one of them is not a gain.

Usage:
    python3 dev/evals/eval_jalength.py out.json          # full run
    SLICE=4 python3 dev/evals/eval_jalength.py out.json  # 4 new cases, then exit
    ITERS=1 python3 dev/evals/eval_jalength.py out.json

Every case is written to the output file as soon as it finishes, so a run that
is killed for memory costs one case, and re-running resumes.
"""
import json
import os
import re
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)          # find the project root by
sys.path.insert(0, _here)                   # marker, not by counting depth
from app.coach import is_clean_verdict                              # noqa: E402
from app.coach.pipeline import call_coach                           # noqa: E402

# (class, short, long, wants). The short text is the eval_jarecall.py probe
# verbatim; the long text contains the short one's erroneous phrase unchanged.
# No `want` may occur in its own input, or the coach quoting the learner back
# would score as a correction — _check_pairs() enforces that before any run.
PAIRS = [
    ("exist", "部屋に猫があります。",
     "友達が来週まで旅行に行っているから、今は私の部屋に猫があります。",
     ["がいます", "猫がいる", "猫はいます"]),
    ("exist", "駅の前に友達があります。",
     "今日は一緒に映画を見る約束をしていて、もう駅の前に友達があります。",
     ["がいます", "友達がい", "友達はいます"]),
    ("exist", "机の上に本がいます。",
     "図書館で借りたのを忘れていたけど、よく見たら机の上に本がいます。",
     ["があります", "本がある", "本はあります"]),
    ("na-adj", "有名の店に行きました。",
     "先週の土曜日は天気がよかったので、家族と一緒に駅の近くの有名の店に行きました。",
     ["有名な"]),
    ("na-adj", "きれいの部屋ですね。",
     "引っ越したばかりだと聞いていたけど、窓も大きいし、きれいの部屋ですね。",
     ["きれいな", "綺麗な"]),
    ("i-adj-neg", "この店は高いじゃないです。",
     "駅から少し遠いけど、料理がとてもおいしいし、この店は高いじゃないです。",
     ["高くない"]),
    ("i-adj-neg", "今日は寒いじゃなかったです。",
     "天気予報では雪が降ると言っていたので心配したけど、今日は寒いじゃなかったです。",
     ["寒くなかった"]),
    ("adverb", "もっと早い歩いてください。",
     "映画が七時に始まるので、このままだと間に合わないから、もっと早い歩いてください。",
     ["早く"]),
    ("adverb", "字を大きい書いてください。",
     "おばあちゃんは目があまりよくないので、手紙を書くときは字を大きい書いてください。",
     ["大きく"]),
    ("time-ni", "先週に京都へ行きました。",
     "大学の友達が久しぶりに日本に来たから、案内するために先週に京都へ行きました。",
     ["先週京都", '先週"', "先週、", "先週へ"]),
    ("time-ni", "毎日に日本語を勉強します。",
     "来年の春に日本の会社で働きたいので、仕事が忙しくても毎日に日本語を勉強します。",
     ["毎日日本語", '毎日"', "毎日、", "毎日勉強"]),
    ("de-exist", "教室で学生がいます。",
     "今日は日曜日なのに、来週テストがあるから、まだ教室で学生がいます。",
     ["教室に"]),
    # Control: a class a deterministic net handles, so it must hold in both
    # arms. If it falls, the harness never reached the coach.
    ("CONTROL", "暗いので、部屋の電気をつきました。",
     "夜遅くに家に帰ったら部屋がとても暗かったので、部屋の電気をつきました。",
     ["つけました"]),
]

# Long and correct, in the same joined-clause style as the long arm, and
# carrying the correct twin of several probe classes (有名な, 高くない,
# 猫がいて, 先週京都へ) — that is where a splitter-plus-net would misfire.
CLEAN = [
    "今日は雨が降っていたので、駅の近くの有名な店でゆっくり昼ご飯を食べました。",
    "来週から新しい仕事が始まるので、毎晩早く寝るようにしています。",
    "友達が遊びに来ると言っていたから、部屋をきれいに掃除しておきました。",
    "このレストランは駅から少し遠いけど、料理がおいしくて、値段も高くないです。",
    "先週京都へ行ったとき、お寺の庭に大きな猫がいて、みんなで写真を撮りました。",
    "会議が長くなりそうなので、先に帰っても大丈夫だと部長に言われました。",
]

ITERS = int(os.environ.get('ITERS', '3'))
SLICE = int(os.environ.get('SLICE', '0'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'


def _check_pairs():
    """Refuse to run a pair that could not measure what it claims to."""
    for _cls, short, long_, wants in PAIRS:
        phrase = short.rstrip('。').split('、')[-1]
        assert phrase in long_, f"long arm lost the error phrase: {short}"
        for text in (short, long_):
            hits = [w for w in wants if w in text]
            assert not hits, f"want {hits} already in the input: {text}"
    assert len({p[2] for p in PAIRS}) == len(PAIRS), "duplicate long sentence"


def _coach_once(text):
    return re.split(r'⬆️\s*Level up:', call_coach(text, "Japanese"))[0]


def _run_case(key, text, wants):
    """Coach `text` ITERS times. With `wants`, count corrections; without,
    count clean verdicts."""
    good = said_clean = 0
    bad = []
    for _ in range(ITERS):
        fb = _coach_once(text)
        clean = is_clean_verdict(fb, "Japanese")
        ok = any(w in fb for w in wants) if wants else clean
        good += ok
        said_clean += clean
        if not ok:
            bad.append(fb.replace('\n', ' | ')[:110])
    return dict(text=text, good=good, clean=said_clean, iters=ITERS, bad=bad[:1])


def main():
    _check_pairs()
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    fresh = 0

    jobs = []
    for cls, short, long_, wants in PAIRS:
        jobs.append(('SHORT::' + short, short, wants, cls))
        jobs.append(('LONG::' + long_, long_, wants, cls))
    jobs += [('CLEAN::' + t, t, None, 'clean') for t in CLEAN]

    for key, text, wants, cls in jobs:
        if key in done:
            continue
        if SLICE and fresh >= SLICE:
            break
        row = _run_case(key, text, wants)
        row['cls'] = cls
        done[key] = row
        fresh += 1
        json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
        verb = 'left alone' if wants is None else 'corrected'
        print(f"{row['good']}/{ITERS} {verb} | [{cls}] {key.split('::')[0]} {text}",
              flush=True)
        if row['bad']:
            print(f"    got: {row['bad'][0]}", flush=True)

    if any(k not in done for k, *_ in jobs):
        print(f"\nINCOMPLETE — {sum(k in done for k, *_ in jobs)} of {len(jobs)} "
              f"cases done. Re-run with the same output file to continue.")
        return 0

    probes = [p for p in PAIRS if p[0] != 'CONTROL']
    n = len(probes) * ITERS
    short_hit = sum(done['SHORT::' + p[1]]['good'] for p in probes)
    long_hit = sum(done['LONG::' + p[2]]['good'] for p in probes)
    long_clean = sum(done['LONG::' + p[2]]['clean'] for p in probes)
    ctrl = [p for p in PAIRS if p[0] == 'CONTROL']
    ctrl_hit = sum(done[a + p[i]]['good'] for p in ctrl
                   for a, i in (('SHORT::', 1), ('LONG::', 2)))
    kept = sum(done['CLEAN::' + t]['good'] for t in CLEAN)

    print(f"\nSHORT corrected : {short_hit}/{n}")
    print(f"LONG  corrected : {long_hit}/{n}   ({long_clean} called 'nothing to fix')")
    print(f"controls        : {ctrl_hit}/{len(ctrl) * 2 * ITERS}")
    print(f"CLEAN left alone: {kept}/{len(CLEAN) * ITERS}")
    print("\nper pair (short -> long):")
    for p in probes:
        s, l = done['SHORT::' + p[1]]['good'], done['LONG::' + p[2]]['good']
        flag = '   <- length hides it' if l < s else ''
        print(f"  {s}/{ITERS} -> {l}/{ITERS}  [{p[0]}] {p[1]}{flag}")

    if ctrl_hit < len(ctrl) * 2 * ITERS:
        print("\n❌ a control lost its correction — the numbers above mean nothing.")
        return 1
    if kept < len(CLEAN) * ITERS:
        print(f"\n❌ over-correction: {len(CLEAN) * ITERS - kept} clean long "
              f"sentence(s) were 'corrected'.")
        return 1
    print(f"\nFinal Long Recall Score: {100.0 * long_hit / n:.1f}% ({long_hit}/{n})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
