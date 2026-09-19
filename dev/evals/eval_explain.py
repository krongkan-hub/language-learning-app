"""Does the listener tell a clear explanation from a vague one?

Explain mode's whole mechanic rests on this. A listener that asks back at
everything is a nag and the mode is unplayable; one that asks back at nothing
is a wall and the learner never gets the second round of output the mode
exists to produce.

The two failures are NOT equally bad, so they are scored separately, the way
the judge suite gates false negatives apart from its headline.

  NAGGING a clear answer is the one that kills the mode. The learner said the
  thing, and is told to say it again. It has its own cap in
  eval_baselines.json and trips the gate on its own.

  LETTING a vague answer pass costs one practice opportunity. The learner
  moves on. It is counted and reported, not gated.

Measured while designing the mode, which is why the prompts are shaped the way
they are:

    English instruction, English content     nagged 0/6
    English instruction, Japanese content    nagged 5/6
    Japanese instruction, Japanese content   nagged 2/6

That middle row is why app/explain.py authors the instruction per language
instead of translating it, and it is the regression this suite exists to
catch. A future edit that routes the listener prompt through a translation
would read fine in English and quietly return the mode to unplayable in
Japanese.
"""
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)          # find the project root by
sys.path.insert(0, _here)                   # marker, not by counting depth
from app.explain import load_topics, listen

ITERS = 3

# (point, learner text, should the listener ask back?)
CASES = {
    'English': [
        ("which forms of transport you use",
         "I take the subway from my house, then I change to a bus for the last part.", False),
        ("which forms of transport you use",
         "I use public transport every morning.", True),
        ("how long the whole journey takes",
         "The whole trip takes about forty minutes door to door.", False),
        ("how long the whole journey takes",
         "It takes a while, depending on the day.", True),
        ("where you change, and to what",
         "I change at Central Station, from the red line to the number 7 bus.", False),
        ("where you change, and to what",
         "I have to change somewhere in the middle.", True),
        ("what time you leave home",
         "I leave home at seven fifteen every weekday.", False),
        ("what time you leave home",
         "I leave pretty early.", True),
        ("what the journey costs",
         "A monthly pass costs sixty euros and covers both the subway and the bus.", False),
        ("what the journey costs",
         "It is not very expensive.", True),
    ],
    'Japanese': [
        ("どんな交通手段を使うか",
         "家から地下鉄に乗って、最後はバスに乗り換えます。", False),
        ("どんな交通手段を使うか",
         "毎朝、公共交通機関を使っています。", True),
        ("全部でどのくらい時間がかかるか",
         "家を出てから職場まで、全部で四十分くらいかかります。", False),
        ("全部でどのくらい時間がかかるか",
         "日によって、けっこうかかります。", True),
        ("どこで何に乗り換えるか",
         "中央駅で、赤い線から七番のバスに乗り換えます。", False),
        ("どこで何に乗り換えるか",
         "途中のどこかで乗り換えないといけません。", True),
        ("何時に家を出るか",
         "平日は毎朝七時十五分に家を出ます。", False),
        ("何時に家を出るか",
         "わりと早めに出ます。", True),
        ("いくらかかるか",
         "定期券は月六十ユーロで、地下鉄もバスも使えます。", False),
        ("いくらかかるか",
         "そんなに高くないです。", True),
    ],
}


def main():
    topic = next(t for t in load_topics() if t.id == 'commute')
    print(f"Running listener check, {ITERS} iterations per case...")
    print("=" * 78)

    right = total = nagged = passed_vague = 0
    per_language = {}
    for language, cases in CASES.items():
        lang_right = lang_total = lang_nag = 0
        for point, text, should_ask in cases:
            asks = 0
            example = ''
            for _ in range(ITERS):
                clear, said = listen(topic, point, text, language)
                if not clear:
                    asks += 1
                    example = example or said
            majority_ask = asks > ITERS / 2
            ok = majority_ask == should_ask
            right += ok
            lang_right += ok
            total += 1
            lang_total += 1
            if not should_ask and majority_ask:
                nagged += 1
                lang_nag += 1
            if should_ask and not majority_ask:
                passed_vague += 1
            mark = 'ok  ' if ok else 'MISS'
            want = 'ASK  ' if should_ask else 'CLEAR'
            print(f"{mark} [{language[:2]}] asked {asks}/{ITERS}  want={want}  {text[:44]}")
            if not ok and not should_ask and example:
                print(f"        nagged with: {example[:66]}")
        per_language[language] = (lang_right, lang_total, lang_nag)
        print("-" * 78)

    for language in sorted(per_language):
        r, t, n = per_language[language]
        print(f"  {language:<10} {r:>2}/{t:<3} = {100*r/t:5.1f}%   nagged {n}")
    print(f"\nnagged a clear answer : {nagged}/{total // 2}")
    print(f"let a vague one pass  : {passed_vague}/{total // 2}")

    # Gated separately, and this one can fail the suite on its own: a listener
    # that asks back at answers already given is the failure that makes the
    # mode unplayable, and a headline can stay respectable while it happens.
    cap = int(os.environ.get('EXPLAIN_MAX_NAG', '4'))
    if nagged > cap:
        print(f"\n❌ nagged {nagged} clear answers, cap is {cap} — the listener is "
              f"asking learners to repeat things they have already said.")
        sys.exit(1)

    print(f"\nFinal Listener Score: {100*right/total:.1f}% ({right}/{total})")


if __name__ == '__main__':
    main()
