# 🆚 VSCode Setup Guide

Complete workflow for working on Job-Hunter Pro in VSCode.

---

## 1. Open Project

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
code .
```

## 2. Install Extensions

`Ctrl+Shift+X`, install:

| Extension | Publisher | Purpose |
|---|---|---|
| Python | Microsoft | Python interpreter + IntelliSense |
| Pylance | Microsoft | Type checking + autocomplete |
| YAML | Red Hat | Validate config.yaml |
| Markdown All in One | Yu Zhang | Preview docs/*.md |
| Markdown Preview Mermaid Support | Matt Bierner | Render diagrams |
| GitLens | GitKraken | Track git history |
| autoDocstring | Nils Werner | Generate docstrings |
| Ruff | Astral | Linter |
| GitLab Workflow | GitLab | MR + CI integration |

## 3. Select Python Interpreter

`Ctrl+Shift+P` → `Python: Select Interpreter` → `.\.venv\Scripts\python.exe`

Bottom-right shows: `Python 3.12.x ('.venv')`.

## 4. Workspace Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".\\.venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "python.analysis.typeCheckingMode": "basic",
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pyc": true,
    "**/.chrome-profile": true,
    "**/.backup_*": true
  },
  "files.associations": {
    "*.yaml": "yaml",
    "*.cmd": "bat"
  },
  "yaml.schemas": {
    "https://json.schemastore.org/yamllint.json": "config.yaml"
  },
  "markdown.preview.fontSize": 14,
  "markdown.preview.theme": "github",
  "editor.formatOnSave": false,
  "editor.rulers": [88],
  "terminal.integrated.defaultProfile.windows": "PowerShell"
}
```

## 5. Debug Configurations

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Web UI",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/run_web.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false
    },
    {
      "name": "Run Bot (CLI)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/run_bot.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false
    },
    {
      "name": "Debug Worker (with breakpoints in linkedin.py)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/run_web.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false,
      "env": {
        "HEADLESS": "false",
        "LOG_LEVEL": "DEBUG"
      }
    }
  ]
}
```

Press **F5** to debug.

## 6. Tasks

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Web UI",
      "type": "shell",
      "command": "python run_web.py",
      "problemMatcher": [],
      "group": { "kind": "build", "isDefault": true }
    },
    {
      "label": "Apply Latest Patch (interactive)",
      "type": "shell",
      "command": "Get-ChildItem patch -Directory | Sort-Object Name -Descending | Select-Object -First 1 | ForEach-Object { Start-Process cmd -ArgumentList '/c', \"$($_.FullName)\\apply.cmd\" }",
      "problemMatcher": []
    },
    {
      "label": "Tail Bot Logs",
      "type": "shell",
      "command": "Get-Content data\\logs\\bot.log -Wait -Tail 50",
      "problemMatcher": []
    },
    {
      "label": "Open Dashboard",
      "type": "shell",
      "command": "Start-Process http://localhost:5050",
      "problemMatcher": []
    },
    {
      "label": "List Patches",
      "type": "shell",
      "command": "Get-ChildItem patch -Directory | Select-Object Name",
      "problemMatcher": []
    },
    {
      "label": "List Backups",
      "type": "shell",
      "command": "Get-ChildItem .backup_* -Directory | Sort-Object Name -Descending | Select-Object Name",
      "problemMatcher": []
    },
    {
      "label": "Saved Answers Count",
      "type": "shell",
      "command": "python -c \"import json; print(f'Saved: {len(json.load(open(\\\"data/answers.json\\\"))}')\"",
      "problemMatcher": []
    }
  ]
}
```

`Ctrl+Shift+P` → `Tasks: Run Task` → pick.
`Ctrl+Shift+B` for default (Run Web UI).

## 7. Recommended Layout

Open these tabs in order:
1. `docs/00_MASTER_CONTINUITY.md` (preview)
2. `config.yaml`
3. `data/logs/bot.log` (with auto-reload)
4. Current file you're editing
5. Terminal pane below (Ctrl+\`)

Split editor (`Ctrl+\`) for code + log side-by-side.

## 8. Workflow

### Morning routine
1. Open VSCode
2. **F5** → "Run Web UI" → opens Chrome
3. Open http://localhost:5050
4. Click 🚀 Start

### Sambil bot run
- Tasks → "Tail Bot Logs" → live updates
- Open `data/answers.json` to watch AI learning

### Debug a failed apply
1. Stop bot
2. Open `packages/extractors/linkedin.py`
3. Set breakpoints (`F9`)
4. **F5** → "Debug Worker"
5. Re-trigger apply
6. Step through (`F10` / `F11`)

### Apply patch
1. Drop ZIP into `patch/`
2. Extract
3. Tasks → "Apply Latest Patch"
4. `Ctrl+Shift+P` → "Developer: Reload Window"
5. **F5** to restart

### Read docs
1. `Ctrl+P` → type `docs/00_INDEX` → enter
2. `Ctrl+Shift+V` for preview
3. `Ctrl+Click` on links to navigate

## 9. Useful Shortcuts

| Action | Shortcut |
|---|---|
| Quick open file | Ctrl+P |
| Quick search symbol | Ctrl+T |
| Go to definition | F12 |
| Find references | Shift+F12 |
| Rename symbol | F2 |
| Multi-cursor | Ctrl+D (next match) |
| Format code | Shift+Alt+F |
| Comment line | Ctrl+/ |
| Split editor | Ctrl+\ |
| Toggle terminal | Ctrl+\` |
| Markdown preview | Ctrl+Shift+V |
| Markdown side preview | Ctrl+K V |

## 10. GitLab Integration

Install **GitLab Workflow** extension. After:
- Bottom-left shows current branch + MR status
- Sidebar shows MR list + issues
- Push triggers CI

```powershell
git remote -v   # verify origin = gitlab
git status
git add docs/
git commit -m "docs: bundle v2 ULTIMATE"
git push origin main
```

## 11. Markdown Tips for Docs Bundle

- `Ctrl+P` then type `@` shows headings in current file
- `Ctrl+Shift+O` shows TOC
- Hover link → `Ctrl+Click` → jump to that doc

## 12. Troubleshooting VSCode

### Python: Activate interpreter doesn't work
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Terminal not finding python
Reload window after setting interpreter.

### Linting errors for selenium imports
Ensure venv selected.

### Markdown preview shows raw text
Install "Markdown All in One" extension.

## 🔗 Related
- [18_DEVELOPMENT_GUIDE.md](18_DEVELOPMENT_GUIDE.md)
- [14_DEVOPS_CICD.md](14_DEVOPS_CICD.md)
