"""
PATCH 9.1 — Updated tests.
Test 1 fix: tailored doesn't mention Helm (since base CV doesn't have it).
"""
import sys
import os

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


# More realistic base CV — longer so word ratio is sane
base_cv_realistic = """
Wahyu Budi Prastowo
IT Infrastructure Specialist at Digiserve

Experienced infrastructure engineer with 8 years of hands-on work in cloud and on-premises environments.

Core expertise: Azure cloud services, Kubernetes orchestration, Docker containerization, Terraform 
infrastructure as code, Ansible configuration management, Helm package management for K8s.

Linux system administration on RHEL, Ubuntu, CentOS. Implemented monitoring with Prometheus and 
Grafana, log aggregation using ELK stack with Elasticsearch, Logstash, Kibana.

Database experience: PostgreSQL, MongoDB, Redis caching. CI/CD pipelines with GitLab CI and 
Jenkins. Network infrastructure: Nginx web server, HAProxy load balancing, NGINX ingress 
controllers for Kubernetes.

Security work: implemented IAM policies, RBAC, OAuth integration, TLS certificate management.
Cloud-native architecture with microservices, autoscaling, observability practices.
"""

# Test 1 (FIXED): tailored uses only existing tech from base CV
tailored_good = {
    "summary": "Senior Cloud Infrastructure Specialist with 8 years Azure expertise and Kubernetes operations",
    "highlighted_skills": ["Azure", "Kubernetes", "Terraform", "Linux", "Helm"],
    "experience_bullets": [
        "Architected Azure cloud infrastructure for 1000+ users at Digiserve",
        "Deployed Kubernetes clusters with Helm charts and Terraform automation",
        "Automated infrastructure provisioning using Terraform and Ansible",
        "Implemented Prometheus and Grafana monitoring stack with ELK logging",
        "Set up Nginx web server with HAProxy load balancing"
    ],
    "key_tools": ["Azure", "Kubernetes", "Docker", "Terraform", "Ansible", "Prometheus", "Grafana", "Helm", "Nginx"]
}

tailored_invents_aws = {
    "summary": "Cloud expert with AWS and Azure experience",
    "highlighted_skills": ["AWS", "Azure", "Kubernetes"],
    "experience_bullets": [
        "Designed AWS Lambda functions for serverless workloads",
        "Migrated to AWS EKS from Azure AKS infrastructure",
        "Used CloudFormation for infrastructure as code",
        "Implemented Prometheus monitoring stack",
        "Managed RDS PostgreSQL instances at scale"
    ],
    "key_tools": ["AWS", "Azure", "Lambda", "CloudFormation", "Prometheus"]
}

tailored_inflates_years = {
    "summary": "Senior architect with 20+ years of cloud experience",
    "highlighted_skills": ["Azure", "Kubernetes"],
    "experience_bullets": [
        "20 years leading infrastructure teams at major companies",
        "Built Azure platforms for enterprises",
        "Deployed Kubernetes at massive scale",
        "Maintained Linux servers across data centers",
        "Used Terraform for infrastructure as code"
    ],
    "key_tools": ["Azure", "Kubernetes", "Linux", "Terraform"]
}

tailored_too_long = {
    "summary": "Senior " * 50,
    "highlighted_skills": ["Azure"] * 30,
    "experience_bullets": ["Built Azure infrastructure with many services and tools and frameworks " * 20] * 5,
    "key_tools": ["Azure"] * 30
}

tailored_missing_key = {
    "summary": "Cloud engineer",
    "highlighted_skills": ["Azure"],
    "key_tools": ["Azure"]
}

tailored_buzzwords = {
    "summary": "World-class expertise in cloud and revolutionary approach to DevOps",
    "highlighted_skills": ["Azure"],
    "experience_bullets": [
        "Led teams of 100+ engineers globally",
        "Built Azure platforms",
        "Managed Kubernetes",
        "Used Terraform",
        "Monitored with Prometheus"
    ],
    "key_tools": ["Azure", "Kubernetes"]
}

# Test 7 (NEW): Variant handling — load balancing/balancer should be OK
tailored_with_variants = {
    "summary": "Infrastructure engineer with 8 years experience in cloud and on-premise",
    "highlighted_skills": ["Azure", "Kubernetes", "Linux"],
    "experience_bullets": [
        "Configured load balancer (HAProxy) for high availability",
        "Set up observability stack with Prometheus and Grafana",
        "Built CI-CD pipelines with GitLab CI",
        "Managed K8s clusters with Helm",
        "Implemented infrastructure-as-code with Terraform"
    ],
    "key_tools": ["Azure", "K8s", "Linux", "Terraform", "Prometheus"]
}

passed = 0
total = 7

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
if test_case("Accepts variants (load balancer/balancing, k8s/kubernetes)",
              base_cv_realistic, tailored_with_variants, True):
    passed += 1

print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} tests passed")
print(f"{'='*50}")

if passed == total:
    print("✅ All tests PASSED")
    sys.exit(0)
else:
    print(f"❌ {total - passed} test(s) FAILED")
    sys.exit(1)
