# 🩹 PATCH 5 — Zombie Recovery + AI URL Token + Reset Button

## 🐛 Issues yang Difix

| Issue | Before | After |
|---|---|---|
| Bot nyangkut, harus manual `Remove-Item state.txt` | ❌ Manual fix | ✅ Auto-detect zombie + Reset button |
| AI endpoint pakai URL-embedded token (VS Code alias) | ❌ Pakai Bearer header → 401 | ✅ Detect URL token, key optional |
| Tidak ada cara cek AI connection tanpa run bot | ❌ Harus run + lihat log | ✅ **Test AI button** di dashboard |
| Tidak tahu kapan state file expired | ❌ Tidak ada timestamp | ✅ Heartbeat (refresh tiap 5s) |
| State file gak ke-cleanup kalau bot crash | ❌ Manual delete | ✅ `atexit` handler + heartbeat detection |
| Dashboard tidak nampilin diagnostic info | ❌ Black box | ✅ Diagnostics panel collapsible |

## 📁 Files

| File | What |
|---|---|
| `packages/ai/provider.py` | URL-embedded token detection + `test_connection()` method |
| `apps/worker/control.py` | Heartbeat + zombie detection + `reset()` + `get_diagnostics()` |
| `apps/worker/runner.py` | Background heartbeat thread + `atexit` cleanup + AI startup test |
| `apps/web/app.py` | `/control/reset` + `/control/ai-test` endpoints + diagnostics |
| `apps/web/templates/dashboard.html` | Reset + Test AI buttons + Diagnostics panel |
| `env.append.txt` | New AI env config snippet |
| `config.snippet.yaml` | New `ai:` block to copy into config.yaml |
| `apply.cmd` | Auto-installer (BATCH) |

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch5
apply.cmd
```

## ⚙️ POST-PATCH Setup (3 steps)

### Step 1: Update `.env`

Buka file `.env` di project root (`C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\.env`),
**replace baris AI**:

```env
AI_API_KEY=
AI_BASE_URL=https://openwebui.tail443aaa.ts.net/api/v1/vscode/sk-3d39a725ffa5e05f-539a83-9e66c5a9
```

> 🔑 Token sekarang di **URL path**, bukan di header. `AI_API_KEY` boleh kosong.

### Step 2: Update `config.yaml`

Replace block `ai:` di config.yaml dengan isi file `config.snippet.yaml` (di folder patch ini).

Key changes:
- `base_url` pakai HTTPS + URL-embedded token
- `api_key: ""` (kosong)

### Step 3: Restart + Test

```powershell
python run_web.py
```

Open http://localhost:5050 → klik **🧠 Test AI** button.

Expected: alert flash green `✅ AI works: 'ready'`

Kalau **❌ 401 Unauthorized** → tokennya invalid (regenerate di OmniRouter)
Kalau **❌ 404** → URL salah / model name salah

## 🎯 NEW Dashboard Features

### 🧹 Reset State Button
Click untuk **force-clear** semua state files (state, command, heartbeat, pid).
Pakai kalau bot stuck dan tombol Start gak respond.

Sebelum PATCH 5 kamu harus:
```powershell
Remove-Item data\.control\state.txt
Remove-Item data\.control\command.txt
```
Sekarang: tinggal klik button 🧹 di dashboard.

### 🧠 Test AI Button
Validasi AI endpoint **tanpa harus run bot**. Cepat (~2 detik).
Output di flash message:
- ✅ AI works: 'ready' → siap dipakai
- ❌ 401 Unauthorized → key/URL salah
- ❌ Connection failed → endpoint down

### 🔧 Diagnostics Panel (collapsible)
Lihat real-time:
- State (idle / running / paused / stopped)
- Last command sent
- PID process bot
- Heartbeat age (kalau >30s → zombie)
- Is zombie flag

## 🧬 Zombie Detection Logic

Sebelum PATCH 5:
```
state.txt = "running"
→ Dashboard show RUNNING badge
→ Click Start → "Bot already running" (padahal udah crash)
→ User harus Remove-Item state.txt
```

Setelah PATCH 5:
```
state.txt = "running" + heartbeat.txt = 60 sec old
→ Auto-detected as ZOMBIE
→ Dashboard show RUNNING + ZOMBIE badge (red)
→ Click Start → auto-reset + start fresh
→ OR click Reset State for manual cleanup
```

Heartbeat di-update setiap 5 detik oleh background thread runner. Kalau bot crash → no more heartbeat → zombie detected dalam 30 detik.

## 🤖 AI URL Token Format

OmniRouter punya 3 jenis endpoint:
| Type | Auth |
|---|---|
| Standard | Bearer token di header |
| **VS Code Alias** ⭐ | Token di URL path |
| API Key | Token di header `x-api-key` |

Kamu pakai **VS Code Alias**:
```
https://openwebui.tail443aaa.ts.net/api/v1/vscode/{TOKEN}/...
```

PATCH 5 auto-detect ini dengan checking `/vscode/` atau `/sk-` di URL. Kalau ketemu → set `api_key="sk-url-embedded"` (placeholder) supaya openai SDK gak complain.

## 🐛 Troubleshooting

### "Test AI" return 401
- Token kamu invalid/expired → generate ulang di OmniRouter dashboard
- Atau URL format salah (cek case sensitive)

### "Test AI" return 404
- Model `antigravity/gemini-3.5-flash-medium` mungkin gak available
- Coba model lain: edit `config.yaml` → `model: "gpt-4o-mini"` atau `claude-3-haiku`

### Bot tetep stuck setelah patch
1. Klik **🧹 Reset State** di dashboard
2. Kalau gak respond → restart `python run_web.py`
3. Kalau masih → kill python process: `Get-Process python | Stop-Process`

### Heartbeat selalu nampilin "no heartbeat"
- Restart bot (state mungkin dari run sebelum patch)
- Patch 5 baru add heartbeat — perlu fresh run

## 📊 Expected Workflow After Patch

```
1. Apply patch
2. Edit .env + config.yaml (AI section)
3. python run_web.py
4. Open dashboard
5. Click "Test AI"
   → ✅ AI works
6. Click "Start"
   → Bot runs with AI fallback enabled
7. Heartbeat updates every 5s
8. If bot crashes → zombie detected in 30s
9. Click "Start" again → auto-recovery
```
