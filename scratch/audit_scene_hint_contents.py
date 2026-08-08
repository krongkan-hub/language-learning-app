import sys
from app.scenarios.builtins import SCENARIOS

def inspect_scene_hints():
    print("=== INSPECTING NON-EMPTY SCENE HINTS ===")
    
    # Check for abstract/vague/meta wording in scene_hints
    vague_keywords = ["sensory", "details", "surround", "environment", "learner", "actor", "scene", "context", "ambiance"]
    
    vague_hints = []
    sensory_concrete_hints = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            sh = t.scene_hint.strip()
            if not sh:
                continue
            if any(vk in sh.lower() for vk in vague_keywords):
                vague_hints.append((s_idx, s.name, t_idx, sh))
            else:
                sensory_concrete_hints.append((s_idx, s.name, t_idx, sh))

    print(f"Total non-empty scene hints: {len(vague_hints) + len(sensory_concrete_hints)}")
    print(f"Vague/Meta scene hints: {len(vague_hints)}")
    print(f"Concrete scene hints: {len(sensory_concrete_hints)}")

    print("\n--- Sample Vague/Meta scene hints ---")
    for item in vague_hints[:20]:
        print(f"  S{item[0]:02d} [{item[1]}] T{item[2]:02d}: '{item[3]}'")

    print("\n--- Sample Concrete scene hints ---")
    for item in sensory_concrete_hints[:15]:
        print(f"  S{item[0]:02d} [{item[1]}] T{item[2]:02d}: '{item[3]}'")

if __name__ == "__main__":
    inspect_scene_hints()
