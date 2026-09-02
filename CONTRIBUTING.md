# Contributing to GitHub Achievements Automation Bot

Thank you for your interest in improving this project! We welcome contributions, feature suggestions, bug reports, and optimizations.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
   - [Reporting Bugs](#reporting-bugs)
   - [Suggesting Enhancements](#suggesting-enhancements)
   - [Pull Requests](#pull-requests)
3. [Development Setup](#development-setup)
4. [Coding Standards & Conventions](#coding-standards--conventions)
5. [Commit Message Guidelines](#commit-message-guidelines)

---

## 📜 Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code. Please review [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

---

## 💡 How Can I Contribute?

### Reporting Bugs
If you encounter unexpected behavior or an issue:
1. Check existing issues to see if it has already been reported.
2. If not, open a new issue using our **Bug Report Template**.
3. Include:
   - Python version and OS.
   - Command flags used.
   - Any sanitised error output (ensure **NO** GitHub tokens or secrets are included in logs!).

### Suggesting Enhancements
Have ideas for new badges, rate-limit optimizations, or interface features?
- Open an issue using the **Feature Request Template**.
- Explain the motivation and suggested implementation.

### Pull Requests
1. Fork the repository.
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-new-feature
   ```
3. Make your changes cleanly and test thoroughly.
4. Verify Python compilation:
   ```bash
   python -m py_compile achievement_bot.py
   ```
5. Commit using descriptive messages (see below).
6. Push your branch to your fork and submit a Pull Request to `main`.

---

## 🛠 Development Setup

1. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/spam-badges.git
   cd spam-badges
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create your local test environment**:
   ```bash
   cp .env.example .env
   # Add your test Personal Access Token to .env
   ```

---

## 🎨 Coding Standards & Conventions

- Follow **PEP 8** style guidelines for Python.
- Use explicit type annotations where appropriate (`typing`).
- Maintain clear docstrings for all functions and classes.
- Ensure terminal output uses `rich` formatting consistently.
- Never hardcode personal secrets, tokens, or credentials.

---

## ✍️ Commit Message Guidelines

We recommend the [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat: add support for custom badge categories`
- `fix: handle 409 conflict during asynchronous PR merge`
- `docs: update troubleshooting guide for background sync`
- `refactor: modularize GraphQL query handlers`
- `chore: update dependencies and github actions`

Thank you for contributing! 🚀
