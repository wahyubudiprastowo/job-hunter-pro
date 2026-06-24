"""PATCH 10 — Self-test for cover_letter_validator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.ai.cover_letter_validator import validate_cover_letter

def test_case(name, **kwargs):
    print(f"\n=== TEST: {name} ===")
    expected = kwargs.pop("expected_valid")
    result = validate_cover_letter(**kwargs)
    status = "✅ PASS" if result.is_valid == expected else "❌ FAIL"
    print(f"{status} — expected valid={expected}, got valid={result.is_valid}")
    if not result.is_valid:
        print(f"   Reasons: {result.reasons}")
    print(f"   Words: {result.word_count}, company: {result.has_company}, jd_ref: {result.has_jd_reference}")
    return result.is_valid == expected


base_cv = """
Wahyu Budi Prastowo — IT Infrastructure Specialist at Digiserve
8 years experience: Azure cloud, Kubernetes, Docker, Terraform, Ansible, Helm.
Linux RHEL/Ubuntu admin. Prometheus + Grafana monitoring. ELK stack.
PostgreSQL, MongoDB. GitLab CI/CD pipelines. Nginx + HAProxy.
IAM, RBAC, OAuth security. Microservices, autoscaling.
"""

jd_realistic = """
Cloud Infrastructure Engineer at TechCorp Berlin.

We are looking for an experienced cloud infrastructure engineer to architect 
and maintain our Azure-based platform. You will deploy Kubernetes clusters,
manage Terraform infrastructure as code, and implement Prometheus monitoring.

Requirements:
- 5+ years Azure cloud
- Kubernetes orchestration
- Terraform IaC
- Linux administration  
- CI/CD pipelines
"""

good_letter = """Dear Hiring Manager,

I was excited to see TechCorp's Cloud Infrastructure Engineer role, particularly the focus on Azure-based platforms and Kubernetes orchestration that aligns perfectly with my background.

In my current role at Digiserve, I have architected Azure cloud infrastructure for over 1000 users, managing Kubernetes clusters with Helm and automating provisioning via Terraform. I implemented Prometheus and Grafana monitoring across our production environment, and built CI/CD pipelines in GitLab. My 8 years of hands-on experience with Linux administration on RHEL and Ubuntu, combined with HAProxy load balancing setups, give me a strong foundation for TechCorp's infrastructure needs.

I would be eager to discuss how my experience can contribute to TechCorp's platform engineering team. I am available for an interview at your convenience.

Sincerely,
Wahyu Budi Prastowo
"""

generic_letter = """Dear Hiring Manager,

I am writing to apply for the Cloud Infrastructure Engineer position. I am a results-driven professional with passion for cloud technology and world-class expertise.

I have extensive experience in cloud platforms and would love to contribute to your team.

Sincerely,
Wahyu
"""

no_company_letter = """Dear Hiring Manager,

I was excited to see this Cloud Engineer role focusing on Azure and Kubernetes that aligns with my background.

At Digiserve I architected Azure infrastructure and deployed Kubernetes clusters with Terraform automation. I implemented Prometheus monitoring stacks and built GitLab CI pipelines. My 8 years of Linux administration provide strong foundation.

I would be eager to discuss how I can contribute. Available for interview.

Sincerely,
Wahyu Budi Prastowo
"""

invents_tech_letter = """Dear Hiring Manager,

TechCorp's Azure infrastructure role excited me. I have deep AWS Lambda experience and managed Snowflake data warehouses for 5 years.

I implemented Kafka streaming pipelines, designed React frontends for internal tools, and built TensorFlow ML models at Digiserve. My PyTorch and Kubernetes expertise spans 8 years.

Available for interview at TechCorp.

Sincerely,
Wahyu
"""

too_short_letter = """Dear Hiring Manager,
I want to apply.
Sincerely,
Wahyu"""

too_long_letter = """Dear Hiring Manager,
""" + ("Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 80) + """
Sincerely, Wahyu"""

italian_letter = """Egregio Responsabile delle Assunzioni,

Sono entusiasta della posizione di Cloud Engineer presso TechCorp Italia, soprattutto per il focus su Azure e Kubernetes che si allinea perfettamente alla mia esperienza.

Presso Digiserve ho architettato infrastrutture Azure per oltre 1000 utenti, gestito cluster Kubernetes con Helm e automatizzato il provisioning con Terraform. Ho implementato Prometheus e Grafana per il monitoring e costruito pipeline CI/CD con GitLab. I miei 8 anni di esperienza con Linux RHEL/Ubuntu e HAProxy mi danno solide basi.

Sarei lieto di discutere come posso contribuire al team TechCorp Italia. Disponibile per un colloquio.

Cordiali saluti,
Wahyu Budi Prastowo
"""

passed = 0
total = 7

if test_case("Good English letter", text=good_letter, company="TechCorp",
              job_description=jd_realistic, cv_text=base_cv, expected_valid=True):
    passed += 1

if test_case("Rejects generic opener + buzzwords", text=generic_letter,
              company="TechCorp", job_description=jd_realistic, cv_text=base_cv,
              expected_valid=False):
    passed += 1

if test_case("Rejects missing company name", text=no_company_letter,
              company="TechCorp", job_description=jd_realistic, cv_text=base_cv,
              expected_valid=False):
    passed += 1

if test_case("Rejects invented tech (AWS/Snowflake/Kafka/React/TF/PyTorch)",
              text=invents_tech_letter, company="TechCorp",
              job_description=jd_realistic, cv_text=base_cv, expected_valid=False):
    passed += 1

if test_case("Rejects too short", text=too_short_letter, company="TechCorp",
              job_description=jd_realistic, cv_text=base_cv, expected_valid=False):
    passed += 1

if test_case("Rejects too long", text=too_long_letter, company="TechCorp",
              job_description=jd_realistic, cv_text=base_cv, expected_valid=False):
    passed += 1

if test_case("Valid Italian letter", text=italian_letter, company="TechCorp",
              job_description=jd_realistic, cv_text=base_cv, expected_valid=True):
    passed += 1

print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} tests passed")
print(f"{'='*50}")
sys.exit(0 if passed == total else 1)
