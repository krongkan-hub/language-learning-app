import re
import sys

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

all_vocab = set()
for si, s in enumerate(SCENARIOS):
    for ti, t in enumerate(s.tasks):
        m = re.match(r"Use the word '(.+)'", t.goal)
        if m:
            all_vocab.add(m.group(1).lower())

print("Check candidate words:")
candidates = ['sommelier', 'ambiance', 'culinary', 'palate', 'pairing', 'courtesy', 'complimentary', 'dosage', 'contraindication', 'adverse', 'efficacy', 'topical', 'amenity', 'amenities', 'concierge', 'surcharge', 'adjoining', 'roast', 'artisan', 'barista', 'extraction', 'steamed', 'brew']
for c in candidates:
    print(f"  {c}: {'TAKEN' if c in all_vocab else 'AVAILABLE'}")
