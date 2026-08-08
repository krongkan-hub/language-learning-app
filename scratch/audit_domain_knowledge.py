import sys
import re
from app.scenarios.builtins import SCENARIOS

def scan_domain_knowledge():
    print("=== 2. DOMAIN KNOWLEDGE VS LANGUAGE AUDIT ===")
    
    keywords = [
        "lapel", "notch", "peak", "shawl", "din release", "harmonized tariff",
        "amortization", "underwriting", "vesting", "cliff", "actuator", "bushing",
        "caliper", "manifold", "synthesizer patch", "camber", "hydrotherapy",
        "reflexology", "astigmatism", "bifocal", "polycarbonate", "refraction",
        "terroir", "tannin", "decanter", "corkage", "acoustical", "pyrotechnics",
        "din", "oem", "escrow", "demurrage", "e-sim", "esim", "vinyasa", "hatha",
        "monstera", "ficus", "encumbrance", "easement"
    ]
    
    pattern = re.compile(r"\b(" + "|".join(keywords) + r")\b", re.IGNORECASE)
    
    findings = []
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            if pattern.search(t.goal) or pattern.search(t.hint):
                findings.append((s_idx, s.name, t_idx, t.goal, t.hint))

    print(f"Total tasks flagged for high domain knowledge / niche specs: {len(findings)}")
    for f in findings:
        print(f"\nS{f[0]:02d} [{f[1]}] Task {f[2]:02d}:")
        print(f"  Goal: {f[3]}")
        print(f"  Hint: {f[4]}")

if __name__ == "__main__":
    scan_domain_knowledge()
