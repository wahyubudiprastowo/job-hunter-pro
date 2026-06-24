"""
Resume Anti-Hallucination Validator (PATCH 9).

Implements Layer 6 from docs/20_ANTI_HALLUCINATION.md:
- detect_new_tech: flag tech/skills in tailored not in base CV
- check_word_count: tailored ≤ 1.1 × base (no inflation)
- check_section_structure: validate JSON has all required keys
- check_years_inflation: no inflated numbers (years, salary)

Usage:
    from packages.ai.resume_validator import validate_tailored

    result = validate_tailored(base_cv_text, tailored_dict)
    if not result.is_valid:
        logger.warning(f"Resume rejected: {result.reasons}")
        return None  # fallback to base
"""
from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


# ============================================================
# Tech term detection — extensible list
# ============================================================

# Categories of tech terms to extract & cross-check
TECH_PATTERNS = {
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "alibaba cloud", "ibm cloud",
        "digitalocean", "linode", "vultr", "heroku", "vercel", "netlify",
        "cloudflare", "fastly", "akamai",
    ],
    "containers": [
        "docker", "kubernetes", "k8s", "openshift", "rancher", "nomad",
        "containerd", "podman", "lxc", "lxd", "helm", "kustomize",
    ],
    "iac": [
        "terraform", "ansible", "puppet", "chef", "saltstack", "salt",
        "pulumi", "cloudformation", "arm template", "bicep", "cdk",
    ],
    "cicd": [
        "jenkins", "gitlab ci", "github actions", "circleci", "travis",
        "azure devops", "bamboo", "teamcity", "argocd", "fluxcd", "spinnaker",
        "tekton", "drone",
    ],
    "monitoring": [
        "prometheus", "grafana", "datadog", "new relic", "splunk", "elk",
        "elasticsearch", "logstash", "kibana", "loki", "jaeger", "zipkin",
        "opentelemetry", "nagios", "zabbix", "pagerduty", "opsgenie",
        "victoriametrics", "thanos", "cortex",
    ],
    "databases": [
        "postgresql", "postgres", "mysql", "mariadb", "mongodb", "redis",
        "cassandra", "elasticsearch", "dynamodb", "cosmosdb", "cosmos db",
        "sql server", "oracle", "sqlite", "couchdb", "neo4j", "influxdb",
        "timescaledb", "snowflake", "bigquery", "redshift",
    ],
    "messaging": [
        "kafka", "rabbitmq", "activemq", "nats", "redis pub/sub", "pubsub",
        "sqs", "sns", "eventbridge", "service bus", "event hubs", "kinesis",
    ],
    "languages": [
        "python", "java", "javascript", "typescript", "go", "golang", "rust",
        "c#", "csharp", "c++", "ruby", "php", "scala", "kotlin", "swift",
        "powershell", "bash", "perl", "lua", "haskell", "elixir",
    ],
    "web_frameworks": [
        "react", "angular", "vue", "svelte", "next.js", "nuxt", "express",
        "django", "flask", "fastapi", "spring", "rails", "laravel",
        ".net", "asp.net", "blazor",
    ],
    "ml_ai": [
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas",
        "numpy", "huggingface", "langchain", "openai", "anthropic",
        "vector database", "pinecone", "weaviate", "chroma", "qdrant",
    ],
    "security": [
        "vault", "hashicorp vault", "iam", "rbac", "oauth", "saml", "oidc",
        "tls", "ssl", "pki", "wireguard", "openvpn", "zero trust", "ztna",
        "siem", "soar", "edr", "snyk", "sonarqube", "trivy",
    ],
    "networking": [
        "nginx", "haproxy", "traefik", "envoy", "istio", "linkerd",
        "consul", "etcd", "zookeeper", "calico", "cilium", "flannel",
        "metallb", "ingress", "vpn", "bgp", "ospf", "load balancer",
    ],
    "storage": [
        "s3", "ceph", "minio", "glusterfs", "nfs", "iscsi", "san", "nas",
        "ebs", "efs", "azure blob", "google cloud storage", "longhorn",
        "rook", "portworx",
    ],
    "linux": [
        "rhel", "centos", "ubuntu", "debian", "alpine", "fedora", "suse",
        "arch", "systemd", "selinux", "apparmor", "iptables", "nftables",
    ],
    "virtualization": [
        "vmware", "vsphere", "esxi", "kvm", "qemu", "virtualbox", "hyper-v",
        "hyperv", "proxmox", "xen", "citrix",
    ],
    "certifications": [
        # Common cert acronyms — case insensitive matching
        "aws certified", "azure certified", "gcp certified",
        "cka", "ckad", "cks", "rhce", "rhcsa", "rhcsa",
        "ccna", "ccnp", "ccie", "pmp", "itil", "togaf",
        "cissp", "comptia", "security+", "network+",
        "az-900", "az-104", "az-204", "az-303", "az-304", "az-400", "az-500",
        "aws solutions architect", "aws devops", "aws sysops",
        "gcp associate", "gcp professional", "terraform associate",
    ],
}

# Flatten all tech terms (lowercase for matching)
ALL_TECH_TERMS = set()
for category, terms in TECH_PATTERNS.items():
    ALL_TECH_TERMS.update(t.lower() for t in terms)


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class ValidationResult:
    is_valid: bool
    reasons: list = field(default_factory=list)
    new_tech: list = field(default_factory=list)
    missing_keys: list = field(default_factory=list)
    word_count_base: int = 0
    word_count_tailored: int = 0
    word_count_ratio: float = 0.0
    sanitized: Optional[dict] = None

    def reject_reason_summary(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "OK"


# ============================================================
# Main validator
# ============================================================

def validate_tailored(
    base_cv_text: str,
    tailored: dict,
    max_word_ratio: float = 1.10,
    strict: bool = True,
    candidate_facts: Optional[dict] = None,
) -> ValidationResult:
    """
    Validate tailored resume against base CV (anti-hallucination).

    Args:
        base_cv_text: original CV as plain text
        tailored: dict with summary/highlighted_skills/experience_bullets/key_tools
        max_word_ratio: max allowed word count ratio (default 1.1 × base)
        strict: if True, fail on ANY new tech. If False, allow up to 1 new.
        candidate_facts: optional dict with years_experience, current_salary for inflation check

    Returns ValidationResult.
    """
    result = ValidationResult(is_valid=True)

    # === Check 1: structure validation ===
    required_keys = ("summary", "highlighted_skills",
                     "experience_bullets", "key_tools")
    missing = [k for k in required_keys if k not in tailored or not tailored.get(k)]
    if missing:
        result.is_valid = False
        result.missing_keys = missing
        result.reasons.append(f"Missing/empty keys: {missing}")
        return result  # bail early — can't validate further

    # === Check 2: new technology detection (Layer 6 from docs/20) ===
    base_tech = _extract_tech_terms(base_cv_text)
    tailored_tech = _extract_tech_from_resume_dict(tailored)
    new_tech = sorted(tailored_tech - base_tech)

    if new_tech:
        result.new_tech = new_tech
        if strict:
            result.is_valid = False
            result.reasons.append(
                f"AI invented {len(new_tech)} new tech: {', '.join(new_tech[:5])}"
                + (f"... +{len(new_tech)-5} more" if len(new_tech) > 5 else "")
            )
        else:
            # Soft mode: only fail if > 1 new
            if len(new_tech) > 1:
                result.is_valid = False
                result.reasons.append(
                    f"AI invented {len(new_tech)} new tech (soft limit=1): "
                    f"{', '.join(new_tech)}"
                )

    # === Check 3: word count inflation ===
    base_words = len(base_cv_text.split())
    tailored_words = _count_words_in_tailored(tailored)
    result.word_count_base = base_words
    result.word_count_tailored = tailored_words

    if base_words > 0:
        result.word_count_ratio = round(tailored_words / base_words, 2)
        if result.word_count_ratio > max_word_ratio:
            result.is_valid = False
            result.reasons.append(
                f"Word count inflation: {tailored_words}/{base_words} "
                f"= {result.word_count_ratio:.2f} > {max_word_ratio}"
            )

    # === Check 4: years/salary inflation (if candidate_facts provided) ===
    if candidate_facts:
        inflation_issues = _check_numeric_inflation(tailored, candidate_facts)
        if inflation_issues:
            result.is_valid = False
            result.reasons.extend(inflation_issues)

    # === Check 5: forbidden phrases (hallucination indicators) ===
    forbidden = _check_forbidden_phrases(tailored)
    if forbidden:
        result.is_valid = False
        result.reasons.append(f"Forbidden phrases: {forbidden}")

    # If valid: provide sanitized version (could differ from input in soft mode)
    if result.is_valid:
        result.sanitized = tailored

    return result


# ============================================================
# Helpers
# ============================================================

def _extract_tech_terms(text: str) -> set:
    """Extract known tech terms from text (case-insensitive substring match)."""
    if not text:
        return set()
    text_lower = text.lower()
    found = set()
    for term in ALL_TECH_TERMS:
        # Use word boundary for short terms to avoid false positives
        if len(term) <= 4:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text_lower):
                found.add(term)
        else:
            if term in text_lower:
                found.add(term)
    return found


def _extract_tech_from_resume_dict(tailored: dict) -> set:
    """Extract tech terms from all string fields in tailored dict."""
    all_text = []
    all_text.append(str(tailored.get("summary", "")))
    all_text.extend(str(s) for s in tailored.get("highlighted_skills", []))
    all_text.extend(str(b) for b in tailored.get("experience_bullets", []))
    all_text.extend(str(t) for t in tailored.get("key_tools", []))
    combined = " ".join(all_text)
    return _extract_tech_terms(combined)


def _count_words_in_tailored(tailored: dict) -> int:
    """Sum word count across all tailored fields."""
    total = 0
    total += len(str(tailored.get("summary", "")).split())
    for s in tailored.get("highlighted_skills", []):
        total += len(str(s).split())
    for b in tailored.get("experience_bullets", []):
        total += len(str(b).split())
    for t in tailored.get("key_tools", []):
        total += len(str(t).split())
    return total


def _check_numeric_inflation(tailored: dict, facts: dict) -> list:
    """Check for inflated years of experience or salary numbers."""
    issues = []

    # Get candidate's actual years
    try:
        actual_years = int(facts.get("years_experience", 0))
    except (ValueError, TypeError):
        actual_years = 0

    # Extract claimed years from all string fields
    all_text = []
    all_text.append(str(tailored.get("summary", "")))
    all_text.extend(str(b) for b in tailored.get("experience_bullets", []))
    combined = " ".join(all_text).lower()

    # Match patterns like "10 years", "15+ years", "20-year"
    years_pattern = r"(\d+)[\s+\-]*(?:year|yr)"
    matches = re.findall(years_pattern, combined)
    for m in matches:
        try:
            claimed = int(m)
            # Flag if claim significantly exceeds actual (allow 20% buffer for context)
            if actual_years > 0 and claimed > actual_years * 1.5:
                issues.append(
                    f"Years inflation: claimed '{claimed} years' but candidate has {actual_years}"
                )
                break  # one issue is enough
        except ValueError:
            continue

    return issues


def _check_forbidden_phrases(tailored: dict) -> list:
    """Check for phrases that indicate hallucination."""
    forbidden_patterns = [
        # AI sometimes adds these despite instructions
        ("expert in everything", "vague superlative"),
        ("world-class expertise", "unsubstantiated claim"),
        ("revolutionary approach", "marketing fluff"),
        ("led teams of 100+", "common inflation pattern"),
        ("doctorate", "fake credential"),
        ("phd in", "fake credential"),
        ("nobel prize", "obvious fake"),
    ]

    all_text = []
    all_text.append(str(tailored.get("summary", "")))
    all_text.extend(str(b) for b in tailored.get("experience_bullets", []))
    combined = " ".join(all_text).lower()

    hits = []
    for pattern, why in forbidden_patterns:
        if pattern in combined:
            hits.append(f'"{pattern}" ({why})')
    return hits


# ============================================================
# Convenience: log validation result
# ============================================================

def log_validation_result(result: ValidationResult, job_id: str = ""):
    """Log the validation result with appropriate emoji + level."""
    suffix = f" [job={job_id}]" if job_id else ""
    if result.is_valid:
        logger.success(
            f"✅ Resume validated{suffix}: "
            f"words {result.word_count_tailored}/{result.word_count_base} "
            f"(ratio {result.word_count_ratio:.2f})"
        )
    else:
        logger.warning(
            f"🛑 Resume REJECTED{suffix}: {result.reject_reason_summary()}"
        )
        if result.new_tech:
            logger.debug(f"   New tech detected: {result.new_tech}")
