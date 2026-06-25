"""Quick seed script for discovered_jobs."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.storage.discovered_jobs import (
    init_schema, save_discovered, list_discovered, get_stats,
)


TEST_JOBS = [
    {"title": "Senior Cloud Infrastructure Engineer", "company": "Stripe",
     "location": "Remote · Worldwide", "fit_score": 92,
     "fit_reasoning": "Strong match: AWS, Terraform, Python",
     "salary": "$160k-200k"},
    {"title": "DevOps Engineer", "company": "Spotify",
     "location": "Stockholm, Sweden", "fit_score": 85,
     "fit_reasoning": "Good match: CI/CD, Docker",
     "salary": "$120k-150k"},
    {"title": "Platform Engineer", "company": "Datadog",
     "location": "Remote · US", "fit_score": 88,
     "fit_reasoning": "Excellent platform background",
     "salary": "$150k-180k"},
    {"title": "Site Reliability Engineer", "company": "GitLab",
     "location": "Remote · EMEA", "fit_score": 78,
     "fit_reasoning": "SRE experience moderate",
     "salary": "$130k-160k"},
    {"title": "Cloud Solutions Architect", "company": "AWS",
     "location": "Singapore", "fit_score": 81,
     "fit_reasoning": "AWS path strong fit",
     "salary": "$140k-170k"},
    {"title": "Kubernetes Administrator", "company": "Red Hat",
     "location": "Remote · APAC", "fit_score": 75,
     "fit_reasoning": "K8s admin solid background",
     "salary": "$110k-140k"},
    {"title": "Junior Web Developer", "company": "Bootcamp Inc",
     "location": "Jakarta, Indonesia", "fit_score": 25,
     "fit_reasoning": "Skill mismatch: junior level",
     "salary": "$30k-40k"},
    {"title": "Marketing Manager", "company": "Generic Corp",
     "location": "Singapore", "fit_score": 15,
     "fit_reasoning": "Unrelated field",
     "salary": "$60k-80k"},
    {"title": "Senior DevOps Engineer SaaS", "company": "Atlassian",
     "location": "Sydney · Remote", "fit_score": 90,
     "fit_reasoning": "Top match: SaaS DevOps",
     "salary": "$170k-210k"},
    {"title": "Infrastructure Engineer", "company": "Cloudflare",
     "location": "London, UK", "fit_score": 87,
     "fit_reasoning": "Network infra strong fit",
     "salary": "$150k-185k"},
]


def main():
    init_schema()
    print("Seeding 10 test jobs...")
    
    added = 0
    timestamp = int(time.time())
    
    for i, template in enumerate(TEST_JOBS, start=1):
        platform = "linkedin" if i % 2 == 1 else "indeed"
        job_data = {
            **template,
            "platform": platform,
            "job_id": f"demo-{platform}-{timestamp}-{i}",
            "url": f"https://www.{platform}.com/jobs/view/demo-{timestamp}-{i}",
            "is_easy_apply": True,
            "description": f"Test job for {template['title']}. " * 5,
        }
        
        row_id = save_discovered(job_data)
        if row_id:
            added += 1
            print(f"  Added [{row_id}] {job_data['title']} @ {job_data['company']} fit={job_data['fit_score']}")
    
    print()
    print(f"Done! Added: {added}")
    print()
    print("Stats:")
    stats = get_stats()
    print(f"  Total: {stats['total']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By platform: {stats['by_platform']}")
    print(f"  Avg fit: {stats['avg_fit_score']}")
    print()
    print("=" * 60)
    print("Next: Refresh http://localhost:5050/discovered")
    print("=" * 60)


if __name__ == "__main__":
    main()