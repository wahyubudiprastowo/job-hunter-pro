"""
In-place patcher for packages/extractors/linkedin.py
Adds cv_text parameter to __init__ and uses build_enriched_facts.

Usage: python patch_linkedin.py
"""
import re
from pathlib import Path

target = Path("packages/extractors/linkedin.py")
if not target.exists():
    print("[ERROR] packages/extractors/linkedin.py not found. Run from project root.")
    exit(1)

content = target.read_text(encoding="utf-8")
original = content

# 1) Update __init__ signature
old_init = "def __init__(self, driver, config, profile, answer_bank, stealth_cfg,\n                 ai_provider=None, ai_config=None):"
new_init = "def __init__(self, driver, config, profile, answer_bank, stealth_cfg,\n                 ai_provider=None, ai_config=None, cv_text=None):"
content = content.replace(old_init, new_init)

# 2) Add cv_text loading after self.ai_cfg = ...
# Find the line "self._candidate_facts = None" and inject CV use before build_candidate_facts
old_block = """        self._candidate_facts = None
        self._answers_file = Path(\"data/answers.json\")"""
new_block = """        self._candidate_facts = None
        self._cv_text = cv_text
        self._answers_file = Path(\"data/answers.json\")"""
content = content.replace(old_block, new_block)

# 3) Update build_candidate_facts call to use enriched version with cv_text
old_call = "self._candidate_facts = build_candidate_facts(profile, answer_bank)"
new_call = "self._candidate_facts = build_candidate_facts(profile, answer_bank, self._cv_text)"
content = content.replace(old_call, new_call)

if content == original:
    print("[WARN] No changes applied — file may already be patched or has different format.")
else:
    backup = target.with_suffix(".py.bak.p6")
    target.rename(backup)
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Patched {target}")
    print(f"[OK] Backup at {backup}")
