# 📄 CV EXTRACTION FIX GUIDE

## 🔍 Issue Found

Your `resumes/base_resume.txt` extracted only **1161 characters** = ~180 words.

A real CV is **3000-6000 chars** typically. The short CV causes:
1. AI doesn't have enough context → over-relies on job title
2. AI invents tech because base CV lacks specifics
3. Validator rejects more (correctly!) because comparison is too sparse

## ✅ Solution Options

### Option A: Regenerate base_resume.txt (RECOMMENDED)

1. Open your full CV (the PDF you usually send to recruiters)
2. Copy ALL text from it
3. Paste into `resumes/base_resume.txt`
4. Should be 3000-6000 chars (~500-1000 words)

### Option B: Convert PDF to better text

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro

# Check current PDF
python -c "
from packages.ai.cv_extractor import extract_cv_text
text = extract_cv_text('resumes/base_resume.pdf')
print('Length:', len(text) if text else 0)
print('First 500 chars:')
print(text[:500] if text else 'EMPTY')
"

# If PDF returns short text, it's image-based
# Either OCR it (requires Tesseract) OR manually create base_resume.txt
```

### Option C: Add CV manually

Create `resumes/base_resume.txt` with this structure:

```
Wahyu Budi Prastowo
IT Infrastructure Specialist at Digiserve
wahyubudiprastowo@gmail.com | Jakarta, Indonesia
LinkedIn: linkedin.com/in/your-profile

SUMMARY
Senior IT Infrastructure Specialist with 8 years of hands-on experience
designing, deploying, and managing enterprise-scale Azure cloud infrastructures.
Expert in Kubernetes orchestration, Terraform IaC, and CI/CD pipelines.
Strong background in Linux administration, monitoring, and security.

EXPERIENCE

Senior IT Infrastructure Specialist | Digiserve | 2018 - Present
- Architected Azure cloud infrastructure for 1000+ users
- Deployed and managed production Kubernetes clusters with Helm
- Implemented Prometheus + Grafana monitoring stack with ELK logging
- Built CI/CD pipelines with GitLab CI and Jenkins
- Automated infrastructure provisioning with Terraform and Ansible
- Managed PostgreSQL, MongoDB databases at scale
- Configured Nginx web servers and HAProxy load balancing
- Implemented IAM policies, RBAC, OAuth for security

[Add previous job experience here]

SKILLS
Cloud: Azure (8 years), hybrid cloud architecture
Containers: Docker, Kubernetes, Helm, Kustomize
IaC: Terraform, Ansible, ARM templates
CI/CD: GitLab CI, Jenkins, GitHub Actions
Monitoring: Prometheus, Grafana, ELK Stack
Languages: Python, Bash, PowerShell, YAML
Databases: PostgreSQL, MongoDB, MySQL, Redis
Networking: Nginx, HAProxy, VPN, BGP
Security: IAM, RBAC, OAuth, TLS/SSL
Linux: RHEL, Ubuntu, CentOS administration
Virtualization: VMware, Hyper-V, KVM

EDUCATION
Bachelor's Degree
[Your university and degree]

CERTIFICATIONS
[Your actual certifications]
```

Save as plain text. Make sure to mention every tech you actually know.

## 🧪 Verify Fix

After updating, test:

```powershell
python -c "
from packages.ai.cv_extractor import extract_cv_text
text = extract_cv_text('resumes/base_resume.pdf')
print('Length:', len(text) if text else 0)
print('Should be 3000-6000 chars')
"
```

Should now show **3000+ chars**.

After fix:
- AI has full context → less invention
- Tailored resumes will reuse YOUR actual tech (not invented)
- Validator reject rate should drop from ~80% to <20%
