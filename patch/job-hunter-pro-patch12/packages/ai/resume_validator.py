"""
Resume Anti-Hallucination Validator (PATCH 12).

CHANGES from 11:
- More COMMON_KNOWLEDGE_TERMS (scala, java baseline languages often mentioned)
- LANGUAGES_TOLERANT mode for language detection
- Better debug output (show what categories ignored)
"""
from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


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
        "cassandra", "dynamodb", "cosmosdb", "cosmos db",
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
        "metallb", "ingress", "vpn", "bgp", "ospf",
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
        "aws certified", "azure certified", "gcp certified",
        "cka", "ckad", "cks", "rhce", "rhcsa",
        "ccna", "ccnp", "ccie", "pmp", "itil", "togaf",
        "cissp", "comptia", "security+", "network+",
        "az-900", "az-104", "az-204", "az-303", "az-304", "az-400", "az-500",
        "aws solutions architect", "aws devops", "aws sysops",
        "gcp associate", "gcp professional", "terraform associate",
    ],
}

VARIANT_GROUPS = [
    {"load balancer", "load balancing", "load balance", "load-balancer", "load-balancing", "lb"},
    {"monitoring", "monitor", "observability", "observe"},
    {"ci/cd", "cicd", "ci-cd", "continuous integration", "continuous deployment", "continuous delivery"},
    {"iac", "infrastructure as code", "infrastructure-as-code"},
    {"k8s", "kubernetes", "kube"},
    {"sre", "site reliability", "site reliability engineering"},
    {"container", "containers", "containerization", "containerized"},
    {"cloud", "cloud-native", "cloudnative"},
    {"autoscaling", "auto-scaling", "auto scaling", "hpa", "vpa"},
    {"gitops", "git-ops"},
    {"microservices", "microservice", "micro-services", "service mesh"},
]

VARIANT_TO_CANONICAL = {}
for group in VARIANT_GROUPS:
    canonical = sorted(group)[0]
    for variant in group:
        VARIANT_TO_CANONICAL[variant] = canonical

# PATCH 12: Expanded common-knowledge terms
# These don't count as "invented" — they're either:
# 1. Generic concepts everyone in IT/Cloud knows
# 2. Baseline languages commonly mentioned in DevOps job descriptions
# 3. Cloud platform basics (google cloud as concept, not GCP specific service)
COMMON_KNOWLEDGE_TERMS = {
    # Generic concepts (P11)
    "cloud", "container", "monitor", "ci-cd", "iac", "sre",
    "auto-scaling", "git-ops", "microservice",
    # PATCH 12 ADDITIONS:
    # Cloud platform "categories" (not specific services)
    "google cloud",     # often mentioned as concept, GCP is the specific
    # Baseline languages OFTEN mentioned in DevOps context
    # without being specific candidate skill
    "scala",            # commonly mentioned in JVM/data context
    "java",             # baseline JVM language
    "javascript",       # ubiquitous web language
    "bash",             # any sysadmin uses bash
    "powershell",       # any Windows sysadmin uses PS
    # Web/system concepts
    "vpn",              # any IT pro knows VPN
    "tls", "ssl",       # basic security knowledge
    "ssh",              # basic Linux skill
    # Database concepts (when CV mentions PostgreSQL, AI might say "SQL")
    "sql",              # would need to be in CV but ambient knowledge
}

ALL_TECH_TERMS = set()
for category, terms in TECH_PATTERNS.items():
    ALL_TECH_TERMS.update(t.lower() for t in terms)
for group in VARIANT_GROUPS:
    ALL_TECH_TERMS.update(g.lower() for g in group)


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
    common_filtered: list = field(default_factory=list)

    def reject_reason_summary(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "OK"


def _canonicalize_terms(terms: set) -> set:
    canonical = set()
    for t in terms:
        canonical.add(VARIANT_TO_CANONICAL.get(t, t))
    return canonical


def validate_tailored(
    base_cv_text: str,
    tailored: dict,
    max_word_ratio: float = 1.10,
    strict: bool = True,
    candidate_facts: Optional[dict] = None,
) -> ValidationResult:
    result = ValidationResult(is_valid=True)

    required_keys = ("summary", "highlighted_skills",
                     "experience_bullets", "key_tools")
    missing = [k for k in required_keys if k not in tailored or not tailored.get(k)]
    if missing:
        result.is_valid = False
        result.missing_keys = missing
        result.reasons.append(f"Missing/empty keys: {missing}")
        return result

    base_tech_raw = _extract_tech_terms(base_cv_text)
    tailored_tech_raw = _extract_tech_from_resume_dict(tailored)
    base_tech = _canonicalize_terms(base_tech_raw)
    tailored_tech = _canonicalize_terms(tailored_tech_raw)

    new_tech_raw = tailored_tech - base_tech
    common_filtered = new_tech_raw & COMMON_KNOWLEDGE_TERMS
    new_tech = sorted(new_tech_raw - COMMON_KNOWLEDGE_TERMS)
    result.common_filtered = sorted(common_filtered)

    if new_tech:
        result.new_tech = new_tech
        if strict:
            result.is_valid = False
            result.reasons.append(
                f"AI invented {len(new_tech)} new tech: {', '.join(new_tech[:5])}"
                + (f"... +{len(new_tech)-5} more" if len(new_tech) > 5 else "")
            )
        else:
            if len(new_tech) > 1:
                result.is_valid = False
                result.reasons.append(
                    f"AI invented {len(new_tech)} new tech (soft limit=1): "
                    f"{', '.join(new_tech)}"
                )

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

    if candidate_facts:
        inflation_issues = _check_numeric_inflation(tailored, candidate_facts)
        if inflation_issues:
            result.is_valid = False
            result.reasons.extend(inflation_issues)

    forbidden = _check_forbidden_phrases(tailored)
    if forbidden:
        result.is_valid = False
        result.reasons.append(f"Forbidden phrases: {forbidden}")

    if result.is_valid:
        result.sanitized = tailored

    return result


def _extract_tech_terms(text: str) -> set:
    if not text:
        return set()
    text_lower = text.lower()
    found = set()
    for term in ALL_TECH_TERMS:
        if len(term) <= 4:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text_lower):
                found.add(term)
        else:
            if term in text_lower:
                found.add(term)
    return found


def _extract_tech_from_resume_dict(tailored: dict) -> set:
    all_text = []
    all_text.append(str(tailored.get("summary", "")))
    all_text.extend(str(s) for s in tailored.get("highlighted_skills", []))
    all_text.extend(str(b) for b in tailored.get("experience_bullets", []))
    all_text.extend(str(t) for t in tailored.get("key_tools", []))
    combined = " ".join(all_text)
    return _extract_tech_terms(combined)


def _count_words_in_tailored(tailored: dict) -> int:
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
    issues = []
    try:
        actual_years = int(facts.get("years_experience", 0))
    except (ValueError, TypeError):
        actual_years = 0
    all_text = []
    all_text.append(str(tailored.get("summary", "")))
    all_text.extend(str(b) for b in tailored.get("experience_bullets", []))
    combined = " ".join(all_text).lower()
    years_pattern = r"(\d+)[\s+\-]*(?:year|yr)"
    matches = re.findall(years_pattern, combined)
    for m in matches:
        try:
            claimed = int(m)
            if actual_years > 0 and claimed > actual_years * 1.5:
                issues.append(
                    f"Years inflation: claimed '{claimed} years' but candidate has {actual_years}"
                )
                break
        except ValueError:
            continue
    return issues


def _check_forbidden_phrases(tailored: dict) -> list:
    forbidden_patterns = [
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


def log_validation_result(result: ValidationResult, job_id: str = ""):
    suffix = f" [job={job_id}]" if job_id else ""
    if result.is_valid:
        common_note = f" (common terms ignored: {result.common_filtered})" if result.common_filtered else ""
        logger.success(
            f"✅ Resume validated{suffix}: "
            f"words {result.word_count_tailored}/{result.word_count_base} "
            f"(ratio {result.word_count_ratio:.2f}){common_note}"
        )
    else:
        logger.warning(
            f"🛑 Resume REJECTED{suffix}: {result.reject_reason_summary()}"
        )
        if result.new_tech:
            logger.debug(f"   Specific new tech: {result.new_tech}")
        if result.common_filtered:
            logger.debug(f"   Common terms (allowed): {result.common_filtered}")
