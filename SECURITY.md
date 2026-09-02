# Security Policy

## Supported Versions

We provide security fixes and maintenance for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

---

## Reporting a Vulnerability

We take the security of this project and your GitHub account seriously.

If you believe you have found a security vulnerability in this project:

1. **Do NOT report security vulnerabilities via public GitHub issues.**
2. Please report the issue privately to the repository maintainer through GitHub's [Private Vulnerability Reporting](https://github.com/RaftFeed/spam-badges/security/advisories/new) or directly to the maintainer via email.
3. Include:
   - A detailed description of the issue.
   - Steps to reproduce or proof-of-concept.
   - Potential impact of the vulnerability.

We will acknowledge receipt within 48 hours and work toward a timely resolution.

---

## Token & Credential Safety Guidelines

- **Never commit `.env` files** or hardcode your GitHub Personal Access Token in the codebase.
- The `.gitignore` file is pre-configured to ignore `.env` files.
- We strongly recommend creating a **dedicated, disposable Personal Access Token** with minimum required scopes (`repo`, `read:user`, `write:discussion`), and revoking it immediately after completing your achievement goals.
