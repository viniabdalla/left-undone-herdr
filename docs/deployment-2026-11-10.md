# SSH deployment — 2026-11-10

Private repository: https://github.com/viniabdalla/left-undone-herdr

| Machine | Result |
|---|---|
| tropico-2 | Development machine, main branch published |
| omarchy2 | Converted the old installation to a Git checkout and preserved the previous copy and local evidence |
| New Omarchy | Created a fresh clone and installed the plugin, skills and command |

The user excluded tropico-1. No installation was pending there.

Both remote machines had the project at `~/Projects/left-undone-herdr`, the command at `~/.local/bin/left-undone` and skills linked for Codex and Claude. Both ran Herdr 0.9.1 with Codex integration v8 and Claude integration updated to v10. All 53 tests passed on each machine. Both could access the private GitHub repository directly with Git.

The validated code was commit `1378776`. Later TODO and report updates did not affect runtime. All three machines tracked `origin/main`. Local installation and test records were in `~/.local/state/left-undone-deploy/`. The old omarchy2 installation was backed up to `~/Projects/left-undone-herdr.backup-20261110-111638`.

Checks covered `left-undone --help` and command resolution in an interactive shell. Both machines had Codex 0.167.0 and Claude 2.1.322. On the new Omarchy, launching without an explicit account exceeded 15 seconds. The direct shim and the launcher with CLAUDE_CONFIG_DIR responded normally. The Left Undone analyzer already selects its verified account through that variable.

This rollout did not repeat a full model cycle on the remote machines. The known stale UUID on Codex session switches remained open. Existing servers and conversations continued running.

## Subsequent updates

From a clean checkout:

```sh
cd ~/Projects/left-undone-herdr
git pull --ff-only
python3 install.py
```

Close and reopen existing panels to load the update. Lists are local and outside the checkout. Updating code does not synchronize them.

### 2026-11-11

tropico-2, omarchy2 and the new Omarchy updated to `70b61a3` with `git pull --ff-only` and `python3 install.py`. The suite passed on all three, with one environment-related skip on the new Omarchy. Open panels require closing and reopening to load the version. The Codex fix after /new and /resume remained only on `fix/codex-active-thread`, outside the installations.
