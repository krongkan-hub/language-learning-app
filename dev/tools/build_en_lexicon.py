"""Rebuild app/lexicon/en_words.txt.gz from a SCOWL release.

The English spelling net (app/coach/nets/spelling.py) needs two things from a
word list: is this token a word at all, and which real word is a typo most
likely meant to be. SCOWL answers both, because every word carries a SIZE
level — 10 is the thousand commonest words, 80 is large-dictionary obscure —
and its licence permits redistribution (the notice ships beside the data as
SCOWL-COPYRIGHT, which the licence requires).

Only levels <= 80 are kept: 95 is where SCOWL puts words "most people will
never use", and a word list that accepts those accepts most typos too. Only
plain a-z words: the net's tokenizer never produces anything else.

    curl -L -o /tmp/scowl.tgz https://downloads.sourceforge.net/wordlist/scowl-2020.12.07.tar.gz
    tar xzf /tmp/scowl.tgz -C /tmp
    python3 dev/tools/build_en_lexicon.py /tmp/scowl-2020.12.07
"""
import glob
import gzip
import os
import re
import sys

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
OUT = os.path.join(_here, 'app', 'lexicon', 'en_words.txt.gz')
MAX_LEVEL = 80


def main(scowl_dir: str) -> None:
    level = {}
    for path in glob.glob(os.path.join(scowl_dir, 'final', '*')):
        name, _, size = os.path.basename(path).rpartition('.')
        if not size.isdigit() or int(size) > MAX_LEVEL or name.startswith('special'):
            continue
        with open(path, encoding='latin-1') as f:
            for word in f:
                word = word.strip().lower()
                if re.fullmatch(r'[a-z]+', word):
                    level[word] = min(level.get(word, 99), int(size))
    # "level<TAB>word", sorted, so a rebuild from the same release is
    # byte-identical and a diff of the data means the data changed.
    body = ''.join(f'{lvl}\t{w}\n' for w, lvl in sorted(level.items()))
    with gzip.GzipFile(OUT, 'wb', mtime=0) as f:
        f.write(body.encode('ascii'))
    print(f'{len(level)} words -> {OUT}')


if __name__ == '__main__':
    main(sys.argv[1])
