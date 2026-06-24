"""
PATCH 9 — Self-test script for resume_validator.

Run from project root:
    python patch/job-hunter-pro-patch9/test_validator.py
"""
import sys
import os

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.ai.resume_validator import validate_tailored, log_validation_result


def test_case(name, base_cv, tailored, expected_valid, **kwargs):
    print(f"\n=== TEST: {name} ===")
    result = validate_tailored(base_cv, tailored, **kwargs)
    status = "✅ PASS" if result.is_valid == expected_valid else "❌ FAIL"
    print(f"{status} — expected valid={expected_valid}, got valid={result.is_valid}")
    if not result.is_valid:
        print(f"   Reasons: {result.reasons}")
    if result.new_tech:
        print(f"   New tech detected: {result.new_tech}")
    print(f"   Word count: {result.word_count_tailored}/{result.word_count_base} = {result.word_count_ratio}")
    return result.is_valid == expected_valid


# Test data
base_cv_realistic = """
Wahyu Budi Prastowo
IT Infrastructure Specialist at Digiserve

8 years of experience with Azure, Kubernetes, Docker, Terraform, Ansible.
Hands-on with Linux administration (RHEL, Ubuntu), Prometheus monitoring,
Grafana dashboards, ELK stack for logging.

Worked with PostgreSQL, MongoDB databases. Implemented CI/CD with GitLab CI.
Network: Nginx, HAProxy load balancing.
"""

# Test 1: Valid — only uses existing tech ✅
tailored_good = {
    "summary": "Senior Cloud Infrastructure Specialist with 8 years Azure expertise",
    "highlighted_skills": ["Azure", "Kubernetes", "Terraform", "Linux"],
    "experience_bullets": [
        "Architected Azure cloud infrastructure for 1000+ users",
        "Deployed Kubernetes clusters with Helm charts",
        "Automated provisioning with Terraform",
        "Implemented Prometheus + Grafana monitoring stack",
        "Set up Nginx load balancers with HAProxy backend"
    ],
    "key_tools": ["Azure", "Kubernetes", "Docker", "Terraform", "Prometheus", "Grafana", "Nginx"]
}

# Test 2: Invalid — adds AWS (not in CV) ❌
tailored_invents_aws = {
    "summary": "Cloud expert with AWS and Azure experience",
    "highlighted_skills": ["AWS", "Azure", "Kubernetes"],
    "experience_bullets": [
        "Designed AWS Lambda functions for serverless",
        "Migrated to AWS EKS from Azure AKS",
        "Used CloudFormation for infrastructure",
        "Implemented Prometheus monitoring",
        "Managed RDS PostgreSQL instances"
    ],
    "key_tools": ["AWS", "Azure", "Lambda", "CloudFormation", "Prometheus"]
}

# Test 3: Invalid — claims 20 years (candidate has 8) ❌
tailored_inflates_years = {
    "summary": "Senior architect with 20+ years of cloud experience",
    "highlighted_skills": ["Azure", "Kubernetes"],
    "experience_bullets": [
        "20 years leading infrastructure teams",
        "Built Azure platforms for enterprises",
        "Deployed Kubernetes at scale",
        "Maintained Linux servers",
        "Used Terraform for IaC"
    ],
    "key_tools": ["Azure", "Kubernetes", "Linux", "Terraform"]
}

# Test 4: Invalid — word count inflation ❌
tailored_too_long = {
    "summary": "Senior " * 50,  # 50 words just in summary
    "highlighted_skills": ["Azure"] * 30,
    "experience_bullets": ["Built Azure infrastructure with many services and tools and frameworks " * 20] * 5,
    "key_tools": ["Azure"] * 30
}

# Test 5: Invalid — missing required key ❌
tailored_missing_key = {
    "summary": "Cloud engineer",
    "highlighted_skills": ["Azure"],
    # missing "experience_bullets"
    "key_tools": ["Azure"]
}

# Test 6: Invalid — forbidden phrase ❌
tailored_buzzwords = {
    "summary": "World-class expertise in cloud and revolutionary approach to DevOps",
    "highlighted_skills": ["Azure"],
    "experience_bullets": [
        "Led teams of 100+ engineers",
        "Built Azure platforms",
        "Managed Kubernetes",
        "Used Terraform",
        "Monitored with Prometheus"
    ],
    "key_tools": ["Azure", "Kubernetes"]
}

# Run tests
passed = 0
total = 6

if test_case("Valid resume (existing tech only)", base_cv_realistic, tailored_good, True):
    passed += 1
if test_case("Rejects AWS hallucination", base_cv_realistic, tailored_invents_aws, False):
    passed += 1
if test_case("Rejects years inflation", base_cv_realistic, tailored_inflates_years, False,
              candidate_facts={"years_experience": "8"}):
    passed += 1
if test_case("Rejects word inflation", base_cv_realistic, tailored_too_long, False):
    passed += 1
if test_case("Rejects missing key", base_cv_realistic, tailored_missing_key, False):
    passed += 1
if test_case("Rejects forbidden buzzwords", base_cv_realistic, tailored_buzzwords, False):
    passed += 1

print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} tests passed")
print(f"{'='*50}")

if passed == total:
    print("✅ All tests PASSED — validator works correctly")
    sys.exit(0)
else:
    print(f"❌ {total - passed} test(s) FAILED — review output above")
    sys.exit(1)
