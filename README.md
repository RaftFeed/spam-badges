# 🏆 GitHub Achievements Automation Bot

An automated tool built with Python to earn available **GitHub Profile Achievement Badges** quickly, cleanly, and safely using GitHub's REST and GraphQL APIs.

---

## 🎯 Badges Overview & Unlock Matrix

| Badge | Achievement Description | Criteria & Tiers | Award Speed | Automation Status |
|:---:|:---|:---|:---:|:---|
| <img src="https://github.githubassets.com/images/modules/profile/achievements/quickdraw-default.png" width="48" alt="Quickdraw"/> | **Quickdraw** | Closed an issue or PR within 5 minutes of opening | **Instant** (< 5m) | ✅ Automatically opens and closes an issue in < 2 seconds |
| <img src="https://github.githubassets.com/images/modules/profile/achievements/yolo-default.png" width="48" alt="YOLO"/> | **YOLO** | Merged a pull request without code review | **Instant** (< 5m) | ✅ Merges a feature branch PR into main without review |
| <img src="https://github.githubassets.com/images/modules/profile/achievements/pull-shark-default.png" width="48" alt="Pull Shark"/> | **Pull Shark** | Merged pull requests:<br>• **Bronze**: 2 PRs<br>• **Silver**: 16 PRs<br>• **Gold**: 128 PRs | **24–48h sync** | ✅ 16 PRs created and merged automatically |
| <img src="https://github.githubassets.com/images/modules/profile/achievements/pair-extraordinaire-default.png" width="48" alt="Pair Extraordinaire"/> | **Pair Extraordinaire** | Co-authored merged pull requests:<br>• **Bronze**: 1 PR<br>• **Silver**: 10 PRs<br>• **Gold**: 24 PRs | **24–48h sync** | ✅ Injects your account into `Co-authored-by:` git trailers |
| <img src="https://github.githubassets.com/images/modules/profile/achievements/galaxy-brain-default.png" width="48" alt="Galaxy Brain"/> | **Galaxy Brain** | Answered discussions marked as accepted answer:<br>• **Bronze**: 2 answers<br>• **Silver**: 8 answers<br>• **Gold**: 16 answers | **Fast** (< 1h) | ⚠️ Requires 2 accounts (GitHub blocks self-answers) |

> [!NOTE]
> **Community / Non-Automatable Badges**:
> - **Starstruck**: Requires 16 / 128 / 512 / 4096 distinct GitHub users to star your repository.
> - **Public Sponsor**: Requires sponsoring an open-source contributor ($1+) on GitHub Sponsors.
> - **Arctic Code Vault / Mars 2020**: Historical archive events (now retired).

---

## 🔍 Why Did Only 2 Badges (Quickdraw & YOLO) Appear Immediately?

If you just ran the bot and only see **Quickdraw** and **YOLO** on your profile:

### 1. Single-Trigger vs. Counter-Aggregated Badges
- **Quickdraw & YOLO** are single-event triggers (1 issue closed in <5m, 1 PR merged without review). GitHub awards them almost in real time (within 1–5 minutes).
- **Pull Shark & Pair Extraordinaire** are **tiered counter badges** (they track milestones: 2, 16, 128 PRs). GitHub processes counter badges through background batch cron jobs. It typically takes **24 to 48 hours** for GitHub's achievement aggregator to refresh your profile.
- You have already met the requirements for 16 merged pull requests in your sandbox repository!

### 2. How Pair Extraordinaire is Credited
- To receive the badge, your GitHub account must be recognized as a **co-author** on a merged pull request.
- The enhanced bot automatically sets the primary commit author to a bot (`github-actions[bot]`) and adds your own verified GitHub username and email to the `Co-authored-by:` git trailer.

### 3. Why Galaxy Brain Requires a 2nd Account (Helper Token)
- GitHub's anti-gaming filter **strictly ignores self-answers**. If you ask a question and mark your own answer as accepted, GitHub will not count it toward Galaxy Brain.
- To automate Galaxy Brain, provide a secondary account token via `--helper-token` or `HELPER_TOKEN` in `.env`. Account 2 will ask the question, your primary account answers it, and Account 2 accepts the answer.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+ installed (`python --version`)
- Required packages:
  ```bash
  pip install -r requirements.txt
  ```

---

### 2. Generate a GitHub Personal Access Token (PAT)

1. Go to [GitHub Settings → Tokens (classic)](https://github.com/settings/tokens).
2. Click **Generate new token (classic)**.
3. Name it: `GitHub Achievements Bot`.
4. Select scopes:
   - `repo` *(Full control of repositories, issues, PRs)*
   - `read:user` *(To fetch your profile handle and ID)*
   - `write:discussion` *(For Discussions)*
5. Click **Generate token** and copy your token (`ghp_...`).

---

### 3. Configure `.env`

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_REPO=github-achievements-sandbox
```

---

## 🎮 Usage

### Interactive CLI Menu
```bash
python achievement_bot.py
```

### Inspect Live Status & Diagnostics
Check the status of your merged PRs and sync status:
```bash
python achievement_bot.py --status
```

### Automate All Badges (Combo)
```bash
# Automate 16 PRs (Silver tier) with Co-author trailers:
python achievement_bot.py --all --prs 16
```

### Automate Galaxy Brain (with 2nd account)
```bash
python achievement_bot.py --badge galaxy-brain --helper-token ghp_secondary_account_token
```

---

## 💡 Pro-Tip to Force GitHub Cache Refresh

Sometimes GitHub caches your profile achievements tab. You can prompt GitHub to re-render your profile:
1. Go to **[github.com/settings/profile](https://github.com/settings/profile)**.
2. Make a small change (e.g., add a space or character to your **Bio** or **Location**).
3. Click **Update profile**.
4. Open an Incognito/Private window and check: `https://github.com/<YOUR_USERNAME>?tab=achievements`.
