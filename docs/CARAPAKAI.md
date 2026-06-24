

🤖 Cara Pakai untuk Prompt LLM (Continuity Test)
Skenario: Lanjut di LLM Baru (Claude / GPT / Cursor / Codex)
Buka session LLM baru, paste prompt ini persis seperti template di bawah:
Master Prompt — Step 1: Orient LLM
Saya melanjutkan project Job-Hunter Pro yang sudah running di production.

Repo: https://gitlab.com/1bulan1m/job-hunter-pro
Local path: C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\

Sebelum kamu coding apapun, WAJIB:

1. Baca docs/00_MASTER_CONTINUITY.md (entry point)
2. Baca docs/CURRENT_STATE_SNAPSHOT.md (apa yang running sekarang)
3. Baca docs/ANTI_BREAKAGE_RULES.md (yang tidak boleh disentuh)
4. Baca docs/AI_HANDOFF_PROTOCOL.md (protocol untuk AI assistant)
5. Baca docs/PATCH_HISTORY_LEDGER.md (track patches)

Konfirmasi kalau sudah selesai baca, lalu beritahu:
- Berapa applied jobs saat ini?
- Phase mana yang sedang berjalan?
- Patch mana yang [INFERRED] dan butuh source code?
- File apa saja yang TIDAK BOLEH disentuh?

Step 2: Cek apa yang mau dikerjakan
Saya mau lanjut ke Phase 2c (Cover Letter Generator).

Sebelum coding:
1. Baca docs/PRDs/PRD_2c_Cover_Letter.md (PRD lengkap)
2. Baca docs/08_PROMPTS_LIBRARY.md section "cover.v1"
3. Baca docs/20_ANTI_HALLUCINATION.md (8 layers)
4. Baca docs/05_PLUGIN_SPEC.md kalau perlu sentuh extractor

Lalu jelaskan ke saya:
- Plan implementasi step-by-step
- Files apa yang dibuat / dimodifikasi
- Acceptance criteria yang harus passed
- Risk assessment (LOW / MEDIUM / HIGH)

Step 3: Konfirmasi anti-breakage
Sebelum kamu mulai coding, konfirmasi:

1. Apakah perubahan ini menyentuh file di ANTI_BREAKAGE_RULES.md "NEVER touch"?
2. Apakah kamu akan create patch di patch/job-hunter-pro-patchN/ (BUKAN edit in-place)?
3. Apakah ada anti-hallucination guard yang relevan (layer mana?)
4. Apa rollback plan kalau patch ini break production?

Kalau semua jawaban OK, baru proceed.

Step 4: Setelah coding done
Sebelum tutup task, update dokumentasi:

1. Update docs/17_CHANGELOG.md dengan entry patch baru
2. Update docs/PATCH_HISTORY_LEDGER.md dengan tabel patch
3. Update docs/PRDs/PRD_2c_Cover_Letter.md → status DONE + acceptance ticked
4. Update docs/CURRENT_STATE_SNAPSHOT.md kalau state berubah signifikan

Lalu commit ke GitLab dengan message convention dari docs/GITLAB_INTEGRATION.md:
"patch N: <semantic description>

- Add: <files>
- Modify: <files>
- Docs: 17_CHANGELOG, PATCH_HISTORY_LEDGER, PRD_2c

Phase: 2c
Acceptance: 5/5 ✅"


📋 Daily Workflow Prompt Template
Untuk pemakaian rutin sehari-hari, simpan template ini:
Pagi — Start bot
Saya mau jalankan bot pagi ini. Help me:
1. Verifikasi production state masih sehat (lihat dashboard via http://localhost:5050)
2. Cek docs/CURRENT_STATE_SNAPSHOT.md update apakah ada perubahan signifikan
3. Saran berapa applies/today yang aman (cek docs/11_SECURITY_PRIVACY.md rate limits)

Siang — Cek progress
Bot udah jalan 2 jam. Help me review:
1. Berapa applied / skipped / failed?
2. Ada error patterns di data/logs/bot.log?
3. Ada screenshots baru di data/screenshots/ (= failure)?
4. Ada question baru di data/unanswered.json yang harus saya jawab manual?

Sore — Improvement
Saya lihat ada [pattern X] yang sering muncul. 
Per docs/PATCH_HISTORY_LEDGER.md, perlu patch baru atau cukup config tuning?

Kalau patch:
- Identify file yang harus diubah
- Cek ANTI_BREAKAGE_RULES.md
- Bikin Risk Assessment per template di sana
- Bikin patch folder + apply.cmd
- Update docs

Kalau config:
- Cek docs/10_CONFIGURATION_SPEC.md
- Saran knob mana yang harus diubah
- Edit config.yaml
- Restart bot

Malam — Wrap-up
Wrap-up hari ini:
1. Update docs/17_CHANGELOG.md kalau ada patch
2. Commit ke GitLab per docs/GITLAB_INTEGRATION.md convention
3. Backup data/applications.db
4. Schedule besok pagi (Phase 3d kalau sudah ada, atau manual)


🗂️ Quick Reference Card
Print/save ini buat referensi cepat:
═══════════════════════════════════════════════════════
  Job-Hunter Pro — Quick Navigation
═══════════════════════════════════════════════════════

🚨 LOST? START HERE:
  docs/00_MASTER_CONTINUITY.md

📸 PRODUCTION STATE:
  docs/CURRENT_STATE_SNAPSHOT.md

🚫 DON'T BREAK:
  docs/ANTI_BREAKAGE_RULES.md

🤖 AI ASSISTANT NEW HERE:
  docs/AI_HANDOFF_PROTOCOL.md

📋 WHAT'S NEXT:
  docs/12_PHASE_ROADMAP.md
  docs/13_CHECKLIST_LIBRARY.md
  docs/PRDs/INDEX.md

🔍 PER-FEATURE SPEC:
  docs/PRDs/PRD_<phase>_<feature>.md

🛠️ TOOLING:
  docs/VSCODE_GUIDE.md
  docs/GITLAB_INTEGRATION.md

📜 ALL PROMPTS:
  docs/08_PROMPTS_LIBRARY.md

🛡️ AI HONESTY:
  docs/20_ANTI_HALLUCINATION.md

═══════════════════════════════════════════════════════