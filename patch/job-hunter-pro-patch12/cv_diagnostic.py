"""
PATCH 12 — CV diagnostic script.
Run this to check your CV state and get specific recommendations.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from packages.ai.cv_extractor import extract_cv_text
from packages.ai.resume_validator import _extract_tech_terms, COMMON_KNOWLEDGE_TERMS


def main():
    print("=" * 60)
    print("CV DIAGNOSTIC")
    print("=" * 60)

    text = extract_cv_text('resumes/base_resume.pdf')
    if not text:
        print("❌ Could not extract CV. Check resumes/base_resume.pdf or .txt")
        return 1

    length = len(text)
    print(f"\n📄 CV length: {length} characters")
    print(f"   Words: {len(text.split())}")
    print(f"   Lines: {len(text.splitlines())}")

    if length < 2000:
        print(f"   ⚠️  TOO SHORT — should be 3000-6000")
        print(f"   This is causing AI to invent tech because lacks context.")
    elif length < 5000:
        print(f"   🟡 OK but could be longer")
    else:
        print(f"   ✅ Good length")

    # Extract tech terms from CV
    tech_terms = _extract_tech_terms(text)
    print(f"\n🔧 Tech terms detected in CV: {len(tech_terms)}")

    if len(tech_terms) < 10:
        print(f"   ⚠️  TOO FEW — most CV should have 20+ tech terms")
        print(f"   Found: {sorted(tech_terms)}")
    elif len(tech_terms) < 20:
        print(f"   🟡 Limited tech coverage")
        print(f"   Found: {sorted(tech_terms)}")
    else:
        print(f"   ✅ Good tech coverage")
        print(f"   First 20: {sorted(tech_terms)[:20]}")

    # Check what's missing
    important_tech = {
        "azure", "kubernetes", "docker", "terraform", "ansible",
        "linux", "ubuntu", "rhel", "git", "python",
        "prometheus", "grafana", "nginx", "haproxy",
        "postgres", "mongodb", "redis"
    }
    missing = important_tech - tech_terms
    if missing:
        print(f"\n🔍 Important tech missing from CV (should add if you know them):")
        print(f"   {sorted(missing)}")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    if length < 3000:
        print("\n1. CRITICAL: Add more content to resumes/base_resume.txt")
        print("   Suggested structure:")
        print("   - Header (name, contact)")
        print("   - Summary (3-5 sentences)")
        print("   - 2-3 jobs with 5+ bullet points each")
        print("   - Skills section (cloud, containers, IaC, monitoring, etc)")
        print("   - Education + Certifications")
    if missing and len(missing) > 5:
        print(f"\n2. Add these skills to your CV if you have them: {sorted(missing)[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
