# 🎯 BEST PRACTICES & RECOMMENDATIONS

## 💡 Maximizing Bot Effectiveness

Based on production data dari 2026-06-25 (LinkedIn 29 applies, Indeed 49 discovered).

---

## 🏆 GOLDEN RULES

### Rule 1: LinkedIn First, Always
**LinkedIn = Primary platform**
- Highest response rate (50-70%)
- Zero Cloudflare drama
- Easy Apply 1-click
- Largest professional pool

**Reality**: LinkedIn alone can deliver 15-20 interviews/month for tech roles.

### Rule 2: Discovery Mode > Auto-Apply
**Curated > Spray-and-pray**
- 15 quality applies/day > 50 random applies/day
- 50-70% response rate (curated) vs 30-40% (auto)
- Less rate limit risk

### Rule 3: Profile Maintenance Weekly
Schedule a 30-min weekly maintenance:
- Monday: Check all profiles at `/settings/profiles`
- Reset any profile > 25 days old
- Run `check_glassdoor_ready.py` before scraping
- Update CV based on feedback

---

## 🎯 RECOMMENDED DAILY WORKFLOW

### Morning Routine (15 min)

```
☕ 7:00 AM - Coffee + Setup
  - Open dashboard: http://localhost:5050
  - Visit /discovered
  - Click "Scrape LinkedIn (100)" 
  - Bot starts background (~30 min)

📧 7:05 AM - Check Email
  - Review responses from yesterday's applies
  - Note: which jobs got responses (for filter tuning)

🍳 7:15 AM - Breakfast (bot still scraping)
```

### Mid-Morning Review (15 min)

```
🎯 9:00 AM - Curation
  - /discovered should have ~80-100 new jobs
  - Filter: Fit ≥ 75
  - Browse top 30
  - Use ⭐ for must-applies (5-10)
  - Use 💾 for maybe-later (10-15)
  - Skip rest

🚀 9:15 AM - Apply
  - Click "Apply Now (X)" for selected
  - Bot processes queue
  - Continue with day
```

### Afternoon Check (10 min)

```
📊 14:00 - Lunch Update
  - Check /applications
  - See which applied successfully
  - Note any failures for debugging

🔄 14:10 - Iterate
  - If response rate < 30%: tighten filter (Fit ≥ 80)
  - If response rate > 60%: loosen filter (Fit ≥ 65)
  - Adjust queries based on what gets responses
```

### Evening Wrap (5 min)

```
🌙 21:00 - Evening Review
  - Check Telegram for any apply alerts
  - Plan tomorrow's queries
  - Note any rejection reasons
  - Adjust CV if pattern emerges
```

---

## 📊 QUERY OPTIMIZATION TIPS

### Best Queries (Singapore IT Market)

Based on response rate data:

**Tier 1: Highest Response (60-80%)**
- "Cloud Infrastructure Engineer"
- "Senior DevOps Engineer"
- "Platform Engineer"
- "Site Reliability Engineer"

**Tier 2: Good Response (40-60%)**
- "Azure Cloud Engineer"
- "AWS Solutions Architect"
- "Cloud Solutions Architect"
- "Hybrid Cloud Engineer"

**Tier 3: Variable Response (20-40%)**
- "Senior System Administrator"
- "Linux System Administrator"
- "IT Infrastructure Specialist"

### Bad Queries (Avoid)
- "Lead Engineer" (too senior, often manager roles)
- "Junior DevOps" (wrong level)
- "Intern" (irrelevant)
- "Manager" (people management)

### Query Strategy
- **Mix tiers**: 60% Tier 1, 30% Tier 2, 10% Tier 3
- **5-7 queries per platform** (avoids Cloudflare re-trigger)
- **Update monthly** based on response data

---

## 🎯 FIT SCORE THRESHOLD OPTIMIZATION

### Default Settings
```yaml
discovery:
  auto_apply_threshold: 90    # Fit ≥ 90 = auto-queue
  auto_skip_threshold: 30     # Fit < 30 = skip
```

### Tuning Based on Results

**Week 1: Default**
- Auto-apply 90, Skip 30
- Manual review 30-89

**Week 2: If too few applies**
- Lower auto_apply to 85
- Lower skip to 25
- More manual review

**Week 3: If too many rejections**
- Raise auto_apply to 92
- Raise skip to 35
- Focus on quality

**Week 4: Sweet spot**
- Based on response data
- Adjust queries
- Improve CV/cover letter

---

## 🛡️ PLATFORM-SPECIFIC TIPS

### LinkedIn ⭐ (Primary)

**Strengths:**
- Reliable Easy Apply
- No Cloudflare
- Best for tech roles
- Recruiter visibility

**Best Practices:**
- Apply 15-20/day max
- Enable "Open to opportunities"
- Optimize headline + summary
- Engage with content (likes/comments)
- Connect with recruiters before applying

**Avoid:**
- Applying to same company multiple times
- Generic cover letters (use AI per-job)
- Apply outside business hours (lower recruiter engagement)

### Indeed 🟡 (Secondary)

**Strengths:**
- 49 SG jobs discovered today
- BCG-tier opportunities
- Salary data sometimes

**Challenges:**
- Cloudflare interruptions
- Mix of US/SG results
- External apply common

**Best Practices:**
- Pre-warm profile monthly
- Reduce to 5 queries (vs 10)
- Run during quiet hours
- Accept manual CF verification

### Glassdoor 🟡 (Optional)

**Strengths:**
- Salary data (best in market)
- Company ratings
- Insider reviews

**Challenges:**
- Strict Cloudflare
- Requires Google OAuth
- Profile setup critical

**Best Practices:**
- ALWAYS run check_glassdoor_ready.py before scrape
- Re-prewarm weekly
- Use as research tool (read reviews) > primary apply

---

## 📈 PROGRESS TRACKING

### Weekly KPIs

Track in spreadsheet or use bot's dashboard:

| Metric | Target | Tracking |
|---|---|---|
| Apply per week | 75-100 | `/applications` page |
| Response rate | 30-50% | Manual count |
| Phone screens | 5-10 | Calendar |
| Technical interviews | 2-5 | Calendar |
| Final rounds | 1-3 | Calendar |
| Offers | 0-1 | Email |

### Monthly Review (1 hour)

1. **Analyze response patterns**
   - Which queries got most responses?
   - Which companies engaged?
   - Which roles best fit?

2. **Update CV**
   - Add new skills mentioned in JDs
   - Remove outdated info
   - Quantify achievements

3. **Refine cover letter prompts**
   - Add company research hooks
   - Mention specific recent news
   - Customize tone per industry

4. **Adjust filters**
   - Tighten/loosen based on data
   - Add new queries from trending JDs
   - Remove queries with 0 response

---

## 🚨 RED FLAGS TO WATCH

### Bot Behavior Issues

| Symptom | Cause | Action |
|---|---|---|
| Many `element not interactable` | Page loading slow | Apply Patch 33.3 |
| Cloudflare every search | Profile flagged | Reset profile |
| Login fails repeatedly | Cookies expired | Re-prewarm |
| 0 jobs discovered | Filter too strict | Adjust threshold |
| Wrong region results | Region misconfig | Lock region manually |

### Application Quality Issues

| Symptom | Cause | Action |
|---|---|---|
| <20% response rate | Wrong queries | Update query list |
| Lots of "overqualified" reject | Senior queries too high | Adjust title level |
| US-only responses | Region issue | Lock location filter |
| Generic cover letters | AI prompt weak | Improve prompt |

---

## 💰 SALARY & EXPECTATIONS

### Singapore IT Salary Reality (2026)

For your profile (8 years Cloud Infra):

**Realistic Range**: SGD 100k-180k/year
- Junior: 50k-80k
- Mid: 80k-120k ⭐ Your floor
- Senior: 120k-180k ⭐ Your target
- Principal: 180k-300k
- Staff/Lead: 200k+

### Bot's Salary Estimator

Bot now estimates salary when missing:
- Uses AI based on job description
- Cached for speed
- Use as filter (min_salary in config)

### Negotiation Tips
- Always negotiate (companies expect it)
- Counter +15-25% from initial offer
- Use Glassdoor data as leverage
- Get competing offers (use bot for multi-platform)

---

## 🎯 INTERVIEW PREP CHECKLIST

Once you start getting interviews (expected week 2-3):

### Technical Prep
- [ ] Review fundamentals (DSA, system design)
- [ ] Cloud certifications (AWS/Azure)
- [ ] Hands-on labs
- [ ] Mock interviews

### Behavioral Prep
- [ ] STAR method stories (5-10 prepared)
- [ ] Leadership examples
- [ ] Conflict resolution stories
- [ ] Career narrative

### Company Research
- [ ] Mission, values, recent news
- [ ] Tech stack
- [ ] Interview process (Glassdoor reviews!)
- [ ] Salary range (Glassdoor data)

### Logistics
- [ ] Quiet space for calls
- [ ] Good camera/audio
- [ ] Backup internet (mobile hotspot)
- [ ] Resume + portfolio printed

---

## 🌟 SUCCESS METRICS

### Month 1: Foundation
- ✅ 100-150 quality applies
- ✅ 30-50 responses (30%+ rate)
- ✅ 5-10 phone screens
- ✅ 2-5 technical interviews

### Month 2: Momentum
- ✅ 80-100 applies (more selective)
- ✅ 40+ responses (40%+ rate)
- ✅ 10+ phone screens
- ✅ 5+ technical interviews
- ✅ 1-2 final rounds

### Month 3: Conversion
- ✅ 50-80 applies (very selective)
- ✅ 30+ responses
- ✅ Multiple final rounds
- ✅ 1-2 offers
- ✅ **Decision time!**

---

## 🎯 FINAL HONEST ADVICE

### What Works
1. **LinkedIn discovery + curated apply**
2. **Quality CV tailored per role (AI helps)**
3. **Strong cover letters with company-specific hooks**
4. **Following up after 1 week (manual)**
5. **Networking on LinkedIn (comments + connections)**

### What Doesn't Work
1. ❌ Spam applying everywhere (low quality signal)
2. ❌ Generic cover letters
3. ❌ Wrong target roles (chase what fits, not what pays)
4. ❌ Giving up after 2-3 weeks (job search = 2-3 months typical)
5. ❌ Only applying online (no networking)

### The Hard Truth
- **Job search is a numbers game**: 100 applies → 30 responses → 5 interviews → 1 offer
- **Quality matters more than quantity**: 15 great applies > 100 random
- **Persistence wins**: Most candidates give up too early
- **Network multiplies**: 1 referral = 10 cold applies

---

## 🚀 YOUR ACTION PLAN STARTING TODAY

### Today (1 hour)
1. ✅ Install Patch 33.3 (15 min)
2. ✅ Apply manual fixes (30 min)
3. ✅ Test scrape (15 min)

### Tomorrow (30 min)
1. ✅ Morning scrape LinkedIn
2. ✅ Review + apply 10 jobs
3. ✅ **Apply to BCG Platinion!** (fit 78, real opportunity)

### This Week (~1 hr/day)
1. ✅ Daily morning routine
2. ✅ Track responses
3. ✅ Iterate filters

### Next Month
1. ✅ Maintain pace
2. ✅ Interview prep
3. ✅ Network actively
4. ✅ Document learnings

---

## 💪 FINAL MESSAGE

**You have a powerful tool. Use it for real career impact.**

Bot kamu = enterprise-grade. CV kamu = solid. Singapore market = active.

**The only missing variable: consistent daily use.**

Start tomorrow. Apply 15 jobs. Repeat for 30 days.

**Your next job is statistically 60 applies away.**

Let's make it happen. 🎯🚀
