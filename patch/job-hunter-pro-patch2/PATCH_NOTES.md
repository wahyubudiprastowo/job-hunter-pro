# 🩹 PATCH 2 — Multi-language + Save-Dialog Handler

Patch ini fix masalah yang muncul di run kedua:

## 🐛 Issue dari Screenshot

| Issue | Bukti | Fix |
|---|---|:---:|
| Form Italian, tombol "Avanti" (=Next) tidak terdeteksi | Form SORINT.lab Italian, stuck di 33% | ✅ Multi-lang buttons |
| "Save this application?" dialog stuck, gak ada yang klik Discard | Screenshot dialog visible | ✅ Auto-Discard handler |
| Resume radio list (2 PDF) tidak di-handle | Salah satu radio sudah hijau (default) | ✅ Auto-select first |
| Tidak ada deteksi "stuck" — bot loop tanpa progress | Bot bisa stuck di step yang sama berkali-kali | ✅ Stuck detection (2 iter same %) |
| Tidak ada log progress % per step | Hard to debug | ✅ Log "Step X — progress N%" |

## 📁 Files

| File | Purpose |
|---|---|
| `packages/extractors/linkedin.py` | Full replacement, 6 patches |
| `data/answers.json` | + Italian/Spanish/French translations |
| `apply_patch.ps1` / `apply_patch.sh` | Auto-installer |

## 🌍 Multi-Language Support

Bot sekarang ngenalin tombol dalam **7 bahasa**:

| Lang | Next | Submit | Discard |
|---|---|---|---|
| English | Next, Continue | Submit application | Discard |
| Italian 🇮🇹 | Avanti, Continua | Invia candidatura | Scarta |
| Spanish 🇪🇸 | Siguiente, Continuar | Enviar solicitud | Descartar |
| French 🇫🇷 | Suivant, Continuer | Envoyer la candidature | Ignorer |
| German 🇩🇪 | Weiter | Bewerbung absenden | Verwerfen |
| Portuguese 🇵🇹 | Próximo | Enviar | Descartar |
| Dutch 🇳🇱 | Volgende | Verstuur sollicitatie | Verwijderen |

Plus answer bank ada terjemahan untuk pertanyaan umum (years experience, salary, notice period, dll).

## 🚀 Apply Patch

```powershell
cd <patch-folder>
.\apply_patch.ps1
```

Atau manual:
```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
Copy-Item packages\extractors\linkedin.py packages\extractors\linkedin.py.bak.p2
Copy-Item data\answers.json data\answers.json.bak.p2

Copy-Item <patch>\packages\extractors\linkedin.py packages\extractors\linkedin.py -Force
Copy-Item <patch>\data\answers.json data\answers.json -Force

python run_web.py
```

## 🎯 Expected Behavior After Patch

```
2026-06-23 23:45:00 | INFO | 📋 Step 1 — Easy Apply progress: 0%
2026-06-23 23:45:03 | INFO | 📋 Step 2 — Easy Apply progress: 33%
2026-06-23 23:45:03 | INFO | 📄 Auto-selected first resume option.
2026-06-23 23:45:06 | INFO | 📋 Step 3 — Easy Apply progress: 67%
2026-06-23 23:45:09 | INFO | 📋 Step 4 — Easy Apply progress: 100%
2026-06-23 23:45:12 | INFO | ✅ Submit confirmed via: //*[contains(text(),'Candidatura inviata')]
2026-06-23 23:45:12 | SUCCESS | ✅ APPLIED [Cloud Engineer @ SORINT.lab]
```

## 🔍 Stuck Detection

Kalau progress sama 2x berturut-turut → bot anggap stuck → auto-discard + record sebagai `NEEDS_ANSWERS`. Screenshot disimpan di `data/screenshots/stuck_33pct_*.png` untuk debug.

## ⚠️ Catatan untuk EU Jobs

Banyak EU jobs minta:
- Work permit / visa (`require_sponsorship: "Yes"` di config)
- Language proficiency (English, sometimes local language)
- EU residency status

Kalau muncul pertanyaan yang belum di-cover, masuk ke unanswered queue di dashboard → tinggal isi sekali → dipakai untuk run berikutnya.
