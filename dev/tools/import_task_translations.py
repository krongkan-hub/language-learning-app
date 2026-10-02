"""Merge authored task translations into the scenario catalogue (OPEN-42).

    python3 dev/tools/import_task_translations.py DIR [--language Japanese] [--check]

DIR holds one file per scenario, named like the catalogue's
(scenario_01.json ...), each a list of {"i", "goal", "hint"} in task order.
Every file is validated before anything is written: one entry per task, same
order, non-empty, in the right script, and no Latin words beyond the fixed
forms Japanese uses as-is (Wi-Fi, USB, ...). A file that fails is reported and
skipped; the others are written. --check validates without writing.

The translations land on each task as {"translations": {"Japanese":
{"goal", "hint"}}}; app/llm/translate.py uses them instead of asking the
model at session start.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / 'app' / 'scenarios' / 'data'

# Latin-letter forms Japanese writes as they are. Anything else in Latin
# letters is an untranslated word.
ALLOWED_LATIN = {
    'wi-fi', 'wifi', 'usb', 'sim', 'pin', 'qr', 'id', 'pc', 'tv', 'cd', 'dvd',
    'gps', 'atm', 'e', 'k', 'g', 'cm', 'mm', 'm', 'km', 'kg', 'ml', 'l', 'gb',
    'tb', 'mb', 'hz', 'w', 'v', 'a', 'b', 'c', 'x', 'xl', 's', 'ok', 'faq', 'it',
    'hdmi', 'led', 'lcd', 'oled', 'hdr', 'iso', 'vip', 'dj', 'nda', 'roi', 'kpi',
    'sns', 'pdf', 'url', 'app', 'ai', 'ceo', 'cto', 'cfo', 'hr', 'pr', 'it', 'ev',
    'suv', 'abs', 'spf', 'uv', 'bmi', 'mri', 'x線', 'cpr', 'aed', 'etc', 'eta',
    'no', 'vat', 'pos', 'id番号', 'bpm', 'fps', 'rpm', 'ssd', 'hdd', 'ram', 'cpu',
    'nfc', 'esim', 'diy', 'ipa', 'lgbtq', 'dna', 'pcr', 'pm', 'am', 'ph',
    'ic', 'ih', 'sms', 'obd-ii', 'api', 'u', 'psi', 'bgm', 'd', 'r', 'pg-',
}
_LATIN_WORD = re.compile(r'[A-Za-z][A-Za-z\-]*')
_JA = re.compile('[぀-ヿ一-鿿]')
# Simplified-only forms that turn up when a model drifts into Chinese.
_SIMPLIFIED = re.compile('[们这说时间对为发过还进让给谁钱买卖车门见问请应该]')


def problems(entries: list, tasks: list, language: str) -> list:
    out = []
    if len(entries) != len(tasks):
        return [f'{len(entries)} entries for {len(tasks)} tasks']
    for k, e in enumerate(entries):
        if e.get('i') != k:
            out.append(f'entry {k}: i={e.get("i")}')
            continue
        for field in ('goal', 'hint'):
            text = (e.get(field) or '').strip()
            if not text:
                out.append(f'task {k} {field}: empty')
                continue
            if language == 'Japanese':
                if not _JA.search(text):
                    out.append(f'task {k} {field}: no Japanese script: {text!r}')
                if _SIMPLIFIED.search(text):
                    out.append(f'task {k} {field}: simplified Chinese: {text!r}')
                vocab = (tasks[k].get('vocab_translations') or {}).get('Japanese') or []
                for w in _LATIN_WORD.findall(text):
                    if w.lower() not in ALLOWED_LATIN and not any(w in v for v in vocab):
                        out.append(f'task {k} {field}: Latin word {w!r}: {text!r}')
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('dir', type=Path)
    ap.add_argument('--language', default='Japanese')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)

    bad = 0
    written = 0
    for path in sorted(args.dir.glob('scenario_*.json')):
        target = CATALOGUE / path.name
        data = json.loads(target.read_text(encoding='utf-8'))
        entries = json.loads(path.read_text(encoding='utf-8'))
        issues = problems(entries, data['tasks'], args.language)
        if issues:
            bad += 1
            print(f'✗ {path.name}: {len(issues)} problem(s)')
            for line in issues[:12]:
                print('   ', line)
            continue
        if args.check:
            print(f'✓ {path.name}')
            continue
        for task, e in zip(data['tasks'], entries):
            task.setdefault('translations', {})[args.language] = {
                'goal': e['goal'].strip(), 'hint': e['hint'].strip()}
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written += 1
    print(f'{written} written, {bad} with problems')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
