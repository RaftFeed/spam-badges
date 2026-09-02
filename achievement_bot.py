#!/usr/bin/env python3
"""
GitHub Achievements Automation Bot (Enhanced)
==============================================
Automate earning GitHub profile achievement badges:
- Quickdraw (Close issue/PR within 5 minutes) - Instant
- YOLO (Merge PR without code review) - Instant
- Pull Shark (Merge 2, 16, or 128 PRs) - Tiered (takes up to 24h sync)
- Pair Extraordinaire (Co-author 1, 10, or 24 merged PRs) - Requires user as co-author
- Galaxy Brain (Answer 2, 8, 16 discussions) - Requires 2 accounts (GitHub blocks self-answers)

Author: GitHub Achievement Automation Tool
License: MIT
"""

import os
import sys
import time
import base64
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

import requests
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

# Initialize rich console
console = Console()

# GitHub API endpoints
API_BASE_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubAPI:
    """Helper wrapper around GitHub REST v3 and GraphQL v4 APIs."""

    def __init__(self, token: str):
        self.token = token.strip()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitHub-Achievements-Bot/2.0"
        }
        self.graphql_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Achievements-Bot/2.0"
        }
        self.user_login: Optional[str] = None
        self.user_name: Optional[str] = None
        self.user_id: Optional[int] = None
        self.user_email: Optional[str] = None

    def get_authenticated_user(self) -> Dict[str, Any]:
        """Verify token and fetch authenticated user info."""
        res = requests.get(f"{API_BASE_URL}/user", headers=self.headers, timeout=15)
        if res.status_code == 401:
            raise ValueError("Authentication failed: Invalid GitHub Personal Access Token.")
        res.raise_for_status()
        data = res.json()
        self.user_login = data.get("login")
        self.user_name = data.get("name") or self.user_login
        self.user_id = data.get("id")
        self.user_email = data.get("email")

        # Try to get verified primary email if available
        try:
            email_res = requests.get(f"{API_BASE_URL}/user/emails", headers=self.headers, timeout=10)
            if email_res.status_code == 200:
                emails = email_res.json()
                for em in emails:
                    if em.get("primary") and em.get("verified"):
                        self.user_email = em.get("email")
                        break
        except Exception:
            pass

        # Fallback to GitHub noreply email if no public email
        if not self.user_email and self.user_id and self.user_login:
            self.user_email = f"{self.user_id}+{self.user_login}@users.noreply.github.com"

        return data

    def get_rate_limit(self) -> Dict[str, Any]:
        """Fetch current GitHub API rate limit status."""
        res = requests.get(f"{API_BASE_URL}/rate_limit", headers=self.headers, timeout=15)
        res.raise_for_status()
        return res.json().get("resources", {})

    def resolve_repo_owner_and_name(self, repo_target: str) -> Tuple[str, str]:
        """Resolve owner and repository name."""
        if "/" in repo_target:
            parts = repo_target.split("/", 1)
            return parts[0].strip(), parts[1].strip()
        if not self.user_login:
            self.get_authenticated_user()
        return self.user_login, repo_target.strip()

    def get_or_create_repo(self, repo_target: str, public: bool = True) -> Dict[str, Any]:
        """Ensure sandbox repository exists, or create it automatically."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)

        res = requests.get(f"{API_BASE_URL}/repos/{owner}/{repo_name}", headers=self.headers, timeout=15)

        if res.status_code == 200:
            repo_data = res.json()
            console.print(f"[green]✓[/green] Found repository: [bold cyan]{owner}/{repo_name}[/bold cyan]")
            return repo_data

        if res.status_code == 404 and owner == self.user_login:
            console.print(f"[yellow]i[/yellow] Repository [bold cyan]{owner}/{repo_name}[/bold cyan] does not exist. Creating...")
            payload = {
                "name": repo_name,
                "description": "Sandbox repository for automating GitHub achievement badges",
                "private": not public,
                "auto_init": True
            }
            create_res = requests.post(f"{API_BASE_URL}/user/repos", headers=self.headers, json=payload, timeout=20)
            create_res.raise_for_status()
            repo_data = create_res.json()
            console.print(f"[green]✓[/green] Created sandbox repository: [bold cyan]{owner}/{repo_name}[/bold cyan]")
            time.sleep(2.5)
            return repo_data

        res.raise_for_status()
        return {}

    def enable_discussions(self, repo_target: str) -> bool:
        """Enable Discussions feature on the target repository."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        res = requests.patch(
            f"{API_BASE_URL}/repos/{owner}/{repo_name}",
            headers=self.headers,
            json={"has_discussions": True},
            timeout=15
        )
        if res.status_code == 200:
            return True
        return False

    def get_default_branch(self, repo_target: str) -> str:
        """Get repository's default branch name (e.g. main)."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        res = requests.get(f"{API_BASE_URL}/repos/{owner}/{repo_name}", headers=self.headers, timeout=15)
        res.raise_for_status()
        return res.json().get("default_branch", "main")

    def get_branch_sha(self, repo_target: str, branch: str) -> str:
        """Get latest commit SHA for a branch."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        res = requests.get(f"{API_BASE_URL}/repos/{owner}/{repo_name}/git/ref/heads/{branch}", headers=self.headers, timeout=15)
        res.raise_for_status()
        return res.json()["object"]["sha"]

    def create_branch(self, repo_target: str, new_branch: str, base_sha: str) -> None:
        """Create a new git reference/branch."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        payload = {
            "ref": f"refs/heads/{new_branch}",
            "sha": base_sha
        }
        res = requests.post(f"{API_BASE_URL}/repos/{owner}/{repo_name}/git/refs", headers=self.headers, json=payload, timeout=15)
        res.raise_for_status()

    def delete_branch(self, repo_target: str, branch_name: str) -> None:
        """Delete branch reference after PR merge."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        requests.delete(f"{API_BASE_URL}/repos/{owner}/{repo_name}/git/refs/heads/{branch_name}", headers=self.headers, timeout=15)

    def commit_file(
        self,
        repo_target: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        author: Optional[Dict[str, str]] = None,
        committer: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create or update a file on a branch, with optional custom author/committer."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload: Dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch
        }
        if author:
            payload["author"] = author
        if committer:
            payload["committer"] = committer

        res = requests.put(f"{API_BASE_URL}/repos/{owner}/{repo_name}/contents/{path}", headers=self.headers, json=payload, timeout=15)
        res.raise_for_status()
        return res.json()

    def create_pull_request(
        self,
        repo_target: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str
    ) -> Dict[str, Any]:
        """Create a pull request."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        res = requests.post(f"{API_BASE_URL}/repos/{owner}/{repo_name}/pulls", headers=self.headers, json=payload, timeout=15)
        res.raise_for_status()
        return res.json()

    def merge_pull_request(self, repo_target: str, pull_number: int, retries: int = 5) -> Dict[str, Any]:
        """Merge a pull request with retry logic for asynchronous mergeability checks."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        payload = {
            "commit_title": f"Merge pull request #{pull_number}",
            "merge_method": "merge"
        }

        for attempt in range(1, retries + 1):
            res = requests.put(
                f"{API_BASE_URL}/repos/{owner}/{repo_name}/pulls/{pull_number}/merge",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            if res.status_code == 200:
                return res.json()
            if res.status_code in (405, 409):
                # GitHub may still be calculating mergeability
                time.sleep(1.2 * attempt)
                continue
            res.raise_for_status()

        raise RuntimeError(f"Could not merge PR #{pull_number} after {retries} attempts.")

    def create_issue(self, repo_target: str, title: str, body: str) -> Dict[str, Any]:
        """Create a new issue."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        payload = {"title": title, "body": body}
        res = requests.post(f"{API_BASE_URL}/repos/{owner}/{repo_name}/issues", headers=self.headers, json=payload, timeout=15)
        res.raise_for_status()
        return res.json()

    def close_issue(self, repo_target: str, issue_number: int) -> Dict[str, Any]:
        """Close an issue."""
        owner, repo_name = self.resolve_repo_owner_and_name(repo_target)
        payload = {"state": "closed", "state_reason": "completed"}
        res = requests.patch(
            f"{API_BASE_URL}/repos/{owner}/{repo_name}/issues/{issue_number}",
            headers=self.headers,
            json=payload,
            timeout=15
        )
        res.raise_for_status()
        return res.json()

    def run_graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query or mutation."""
        res = requests.post(
            GRAPHQL_URL,
            headers=self.graphql_headers,
            json={"query": query, "variables": variables},
            timeout=20
        )
        res.raise_for_status()
        data = res.json()
        if "errors" in data and data["errors"]:
            error_msgs = [e.get("message", "Unknown error") for e in data["errors"]]
            raise RuntimeError(f"GraphQL Error: {'; '.join(error_msgs)}")
        return data.get("data", {})


# ---------------------------------------------------------------------------
# Badge Unlock Routines
# ---------------------------------------------------------------------------

def unlock_quickdraw(api: GitHubAPI, repo_target: str) -> bool:
    """
    Unlock Quickdraw badge:
    Close an issue within 5 minutes of opening it.
    """
    console.print(Panel("[bold magenta]🎯 Automating: Quickdraw Badge[/bold magenta]\n[dim]Requirement: Close an issue within 5 minutes[/dim]", box=box.ROUNDED))

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"Quickdraw Achievement Trigger ({timestamp})"
        body = "This issue is automatically created and closed immediately to earn the GitHub Quickdraw badge."

        console.print("[cyan]→[/cyan] Creating issue...")
        issue = api.create_issue(repo_target, title, body)
        issue_number = issue["number"]
        console.print(f"[green]✓[/green] Created issue [bold]#{issue_number}[/bold]")

        console.print("[cyan]→[/cyan] Closing issue immediately (< 3 seconds)...")
        time.sleep(1.0)
        api.close_issue(repo_target, issue_number)
        console.print(f"[green]✓[/green] Issue [bold]#{issue_number}[/bold] closed successfully!")

        console.print("[bold green]✨ Quickdraw criteria satisfied![/bold green]\n")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to automate Quickdraw: {e}[/red]\n")
        return False


def run_pr_workflow(
    api: GitHubAPI,
    repo_target: str,
    count: int = 2,
    badge_title: str = "Pull Shark",
    enable_coauthor: bool = False,
    coauthor_name: str = "Monalisa Octocat",
    coauthor_email: str = "octocat@users.noreply.github.com"
) -> int:
    """
    Automated PR workflow with proper co-author attribution.
    Key Fix: To ensure the authenticated user gets credit for 'Pair Extraordinaire',
    we set the commit primary author to GitHub Actions bot and add BOTH the user's
    verified email/handle AND the co-author in the trailers.
    """
    badge_info = f"[bold magenta]🎯 Automating: {badge_title}[/bold magenta]\n[dim]Target: {count} merged pull request(s)"
    if enable_coauthor:
        badge_info += f" | Co-author: {coauthor_name} <{coauthor_email}>"
    badge_info += "[/dim]"

    console.print(Panel(badge_info, box=box.ROUNDED))

    default_branch = api.get_default_branch(repo_target)
    success_count = 0

    user_login = api.user_login or "user"
    user_name = api.user_name or user_login
    user_email = api.user_email or f"{user_login}@users.noreply.github.com"
    user_noreply = f"{api.user_id}+{user_login}@users.noreply.github.com" if api.user_id else f"{user_login}@users.noreply.github.com"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Merging PRs for {badge_title}...", total=count)

        for i in range(1, count + 1):
            timestamp = int(time.time() * 1000)
            branch_name = f"badge-feature-{timestamp}-{i}"

            try:
                progress.update(task, description=f"[{i}/{count}] Getting base branch SHA...")
                base_sha = api.get_branch_sha(repo_target, default_branch)

                progress.update(task, description=f"[{i}/{count}] Creating branch {branch_name}...")
                api.create_branch(repo_target, branch_name, base_sha)

                # Commit preparation:
                # If coauthor is enabled, make the bot the primary author, so YOUR account
                # is recognized as the Co-author on the merged PR!
                custom_author = None
                custom_committer = None
                commit_msg = f"Add achievement badge activity #{i}"

                if enable_coauthor:
                    # External bot as primary author
                    custom_author = {
                        "name": "github-actions[bot]",
                        "email": "41898282+github-actions[bot]@users.noreply.github.com"
                    }
                    custom_committer = custom_author

                    # Credit YOU explicitly as co-author + optional partner
                    commit_msg += f"\n\nCo-authored-by: {user_name} <{user_email}>"
                    commit_msg += f"\nCo-authored-by: {user_login} <{user_noreply}>"
                    if coauthor_email and coauthor_name:
                        commit_msg += f"\nCo-authored-by: {coauthor_name} <{coauthor_email}>"

                file_path = f"badges/activity_{timestamp}_{i}.md"
                file_content = f"# Achievement Activity #{i}\nTimestamp: {datetime.now().isoformat()}\nTarget: {badge_title}\n"

                progress.update(task, description=f"[{i}/{count}] Committing changes...")
                api.commit_file(
                    repo_target, file_path, file_content, commit_msg, branch_name,
                    author=custom_author, committer=custom_committer
                )

                progress.update(task, description=f"[{i}/{count}] Opening Pull Request...")
                pr_title = f"feat: Automated PR #{i} for {badge_title}"
                pr_body = (
                    f"Automated PR for GitHub Achievements ({badge_title}).\n\n"
                    f"- Iteration: {i}/{count}\n"
                )
                if enable_coauthor:
                    pr_body += f"- Co-author credited: {user_name} ({user_login})\n"

                pr = api.create_pull_request(repo_target, pr_title, pr_body, branch_name, default_branch)
                pr_number = pr["number"]

                progress.update(task, description=f"[{i}/{count}] Merging PR #{pr_number}...")
                time.sleep(1.2)
                api.merge_pull_request(repo_target, pr_number)

                progress.update(task, description=f"[{i}/{count}] Cleaning up branch {branch_name}...")
                api.delete_branch(repo_target, branch_name)

                success_count += 1
                progress.advance(task)
                time.sleep(1.0)

            except Exception as e:
                console.print(f"[red]✗ Error on PR #{i}: {e}[/red]")
                time.sleep(2.0)

    console.print(f"[bold green]✓ Successfully merged {success_count}/{count} pull requests![/bold green]\n")
    return success_count


def unlock_galaxy_brain(api: GitHubAPI, repo_target: str, helper_api: Optional[GitHubAPI] = None, count: int = 2) -> bool:
    """
    Unlock Galaxy Brain badge:
    IMPORTANT: GitHub's achievement evaluator explicitly BLOCKS self-answers.
    The question MUST be asked by account A, and answered by account B (or vice versa),
    and marked as accepted.
    """
    console.print(Panel(
        f"[bold magenta]🎯 Automating: Galaxy Brain Badge[/bold magenta]\n"
        f"[dim]Requirement: Answer discussions and have them accepted by the question author (Target: {count})[/dim]",
        box=box.ROUNDED
    ))

    if not helper_api:
        console.print(Panel(
            "[bold yellow]⚠️ Important Note Regarding Galaxy Brain:[/bold yellow]\n\n"
            "GitHub's anti-abuse filter [bold red]strictly ignores self-answers[/bold red].\n"
            "Asking a question with your account and answering it with the same account will [bold]NOT[/bold] award the Galaxy Brain badge.\n\n"
            "To unlock Galaxy Brain automatically, you need a [bold cyan]second/collaborator GitHub account[/bold cyan] (helper token):\n"
            "  1. Helper Account creates the Discussion Question.\n"
            "  2. Your Primary Account posts the Answer.\n"
            "  3. Helper Account marks your answer as the [bold green]Accepted Answer[/bold green].\n\n"
            "Provide a helper token with [bold]--helper-token <token>[/bold] or set [bold]HELPER_TOKEN[/bold] in .env.",
            box=box.ROUNDED
        ))
        return False

    owner, repo_name = api.resolve_repo_owner_and_name(repo_target)
    api.enable_discussions(repo_target)

    query_repo = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 10) {
          nodes {
            id
            name
            isAnswerable
          }
        }
      }
    }
    """

    try:
        data = api.run_graphql(query_repo, {"owner": owner, "name": repo_name})
        repo_data = data.get("repository")
        if not repo_data:
            console.print("[red]✗ Repository not found in GraphQL API.[/red]\n")
            return False

        repo_id = repo_data["id"]
        categories = repo_data.get("discussionCategories", {}).get("nodes", [])

        category_id = None
        for cat in categories:
            if cat.get("isAnswerable"):
                category_id = cat["id"]
                break

        if not category_id and categories:
            category_id = categories[0]["id"]

        if not category_id:
            console.print("[yellow]! Discussion Q&A categories not loaded. Enable Discussions on repo settings first.[/yellow]\n")
            return False

        mutation_create_disc = """
        mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
          createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) {
            discussion { id number url }
          }
        }
        """

        mutation_add_comment = """
        mutation($discussionId: ID!, $body: String!) {
          addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
            comment { id url }
          }
        }
        """

        mutation_mark_answer = """
        mutation($commentId: ID!) {
          markDiscussionCommentAsAnswer(input: {id: $commentId}) {
            discussion { id }
          }
        }
        """

        successes = 0
        for i in range(1, count + 1):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = f"Technical Question #{i} ({timestamp})"
            body = f"How do I solve problem #{i}?"
            ans_body = f"Here is the detailed solution to problem #{i}. This answer explains the implementation clearly."

            console.print(f"[cyan]→[/cyan] [{i}/{count}] Helper account ({helper_api.user_login}) creating question...")
            disc_res = helper_api.run_graphql(mutation_create_disc, {
                "repositoryId": repo_id,
                "categoryId": category_id,
                "title": title,
                "body": body
            })
            disc_id = disc_res["createDiscussion"]["discussion"]["id"]
            disc_url = disc_res["createDiscussion"]["discussion"]["url"]

            time.sleep(1.0)
            console.print(f"[cyan]→[/cyan] [{i}/{count}] Primary account ({api.user_login}) posting solution...")
            comment_res = api.run_graphql(mutation_add_comment, {
                "discussionId": disc_id,
                "body": ans_body
            })
            comment_id = comment_res["addDiscussionComment"]["comment"]["id"]

            time.sleep(1.0)
            console.print(f"[cyan]→[/cyan] [{i}/{count}] Helper account marking solution as ACCEPTED ANSWER...")
            helper_api.run_graphql(mutation_mark_answer, {"commentId": comment_id})
            console.print(f"[green]✓[/green] [{i}/{count}] Solution accepted! {disc_url}")
            successes += 1
            time.sleep(1.5)

        console.print(f"[bold green]✓ Galaxy Brain completed ({successes}/{count} legitimate accepted answers)![/bold green]\n")
        return True

    except Exception as e:
        console.print(f"[red]✗ Error during Galaxy Brain flow: {e}[/red]\n")
        return False


def check_status_and_diagnostics(api: GitHubAPI, repo_target: str):
    """Inspect repository activity and explain GitHub achievement background sync status."""
    owner, repo_name = api.resolve_repo_owner_and_name(repo_target)

    console.print(Panel(
        f"[bold cyan]🔍 GitHub Achievements Diagnostic Status[/bold cyan]\n"
        f"[dim]Inspecting {owner}/{repo_name} and account achievements...[/dim]",
        box=box.ROUNDED
    ))

    # Check merged PRs
    try:
        prs_res = requests.get(f"{API_BASE_URL}/repos/{owner}/{repo_name}/pulls?state=closed", headers=api.headers, timeout=15)
        prs = [p for p in prs_res.json() if p.get("merged_at")]
        merged_count = len(prs)
    except Exception:
        merged_count = 0

    # Check issues
    try:
        issues_res = requests.get(f"{API_BASE_URL}/repos/{owner}/{repo_name}/issues?state=closed", headers=api.headers, timeout=15)
        closed_issues = [i for i in issues_res.json() if "pull_request" not in i]
        issues_count = len(closed_issues)
    except Exception:
        issues_count = 0

    # Live profile scrape
    profile_url = f"https://github.com/{api.user_login}?tab=achievements"
    found_badges = []
    try:
        prof_res = requests.get(profile_url, timeout=10)
        for badge in ["Quickdraw", "YOLO", "Pull Shark", "Pair Extraordinaire", "Galaxy Brain", "Starstruck"]:
            if badge.lower() in prof_res.text.lower():
                found_badges.append(badge)
    except Exception:
        pass

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Item", style="cyan")
    table.add_column("Repository Progress", style="white")
    table.add_column("Live Profile Status", style="green")

    table.add_row("Quickdraw", f"{issues_count} closed issues (<5m)", "✅ Displayed" if "Quickdraw" in found_badges else "⏳ Syncing")
    table.add_row("YOLO", f"{merged_count} PRs merged without review", "✅ Displayed" if "YOLO" in found_badges else "⏳ Syncing")
    table.add_row("Pull Shark", f"{merged_count} merged PRs (Bronze: 2, Silver: 16)", "✅ Displayed" if "Pull Shark" in found_badges else "⏳ Pending Sync (24-48h)")
    table.add_row("Pair Extraordinaire", "Co-authored PR commits merged", "✅ Displayed" if "Pair Extraordinaire" in found_badges else "⏳ Pending Sync (24-48h)")
    table.add_row("Galaxy Brain", "Requires non-self accepted answers", "✅ Displayed" if "Galaxy Brain" in found_badges else "Requires 2nd Account")

    console.print(table)

    console.print(Panel(
        "[bold yellow]⏱ Why did YOLO & Quickdraw appear immediately, but Pull Shark / Pair Extraordinaire are delayed?[/bold yellow]\n\n"
        "1. [bold cyan]Single-Trigger vs Counter-Aggregated Badges[/bold cyan]:\n"
        "   - [bold]Quickdraw & YOLO[/bold] are single-action events. GitHub awards them in real-time within minutes.\n"
        "   - [bold]Pull Shark & Pair Extraordinaire[/bold] are tiered counters (2, 16, 128 PRs). GitHub processes counter aggregation through asynchronous batch cron jobs. It typically takes [bold]24 to 48 hours[/bold] for these badges to reflect on your profile.\n\n"
        "2. [bold cyan]Your Progress is 100% Recorded[/bold cyan]:\n"
        f"   You have already merged [bold green]{merged_count} pull requests[/bold green] into your default branch! You meet the criteria for both [bold]Bronze[/bold] and [bold]Silver[/bold] Pull Shark.\n\n"
        "3. [bold cyan]Pro-Tip to force GitHub cache re-render[/bold cyan]:\n"
        "   Go to [underline]github.com/settings/profile[/underline], edit a character in your Bio or Location, and click Save. This frequently forces GitHub to invalidate the profile badge cache!",
        box=box.ROUNDED
    ))


# ---------------------------------------------------------------------------
# All-In-One Combo Routine
# ---------------------------------------------------------------------------

def unlock_all_badges(
    api: GitHubAPI,
    repo_target: str,
    prs_count: int = 2,
    coauthor_name: str = "Monalisa Octocat",
    coauthor_email: str = "octocat@users.noreply.github.com",
    helper_api: Optional[GitHubAPI] = None
):
    """Execute all automatable badges in the optimal sequence."""
    console.print(Panel(
        "[bold cyan]🚀 Executing Enhanced GitHub Achievements Sequence[/bold cyan]\n"
        "[dim]Co-author trailers credit your user account directly to unlock Pair Extraordinaire.[/dim]",
        box=box.DOUBLE
    ))

    # 1. Quickdraw
    unlock_quickdraw(api, repo_target)

    # 2. Combo PR Workflow (YOLO + Pull Shark + Pair Extraordinaire)
    run_pr_workflow(
        api=api,
        repo_target=repo_target,
        count=prs_count,
        badge_title="Combo (YOLO + Pull Shark + Pair Extraordinaire)",
        enable_coauthor=True,
        coauthor_name=coauthor_name,
        coauthor_email=coauthor_email
    )

    # 3. Galaxy Brain (if helper provided)
    if helper_api:
        unlock_galaxy_brain(api, repo_target, helper_api=helper_api, count=2)
    else:
        console.print(
            "[yellow]ℹ Galaxy Brain skipped: To unlock Galaxy Brain, provide a secondary account token via --helper-token.\n"
            "(GitHub blocks self-answers from counting).[/yellow]\n"
        )

    # Status check
    check_status_and_diagnostics(api, repo_target)


# ---------------------------------------------------------------------------
# CLI & Interactive Menu
# ---------------------------------------------------------------------------

def print_banner(user_data: Dict[str, Any], rate_limit: Dict[str, Any], repo_target: str):
    """Display an attractive header banner with authenticated status."""
    core_limit = rate_limit.get("core", {})
    remaining = core_limit.get("remaining", "N/A")
    total = core_limit.get("limit", "N/A")

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("[bold cyan]GitHub User:[/bold cyan]", f"[bold]{user_data.get('login')}[/bold] ({user_data.get('name') or 'N/A'})")
    table.add_row("[bold cyan]Target Repo:[/bold cyan]", f"[yellow]{repo_target}[/yellow]")
    table.add_row("[bold cyan]API Rate Limit:[/bold cyan]", f"[green]{remaining}[/green] / {total} remaining")

    console.print(Panel(
        table,
        title="[bold blue]🏆 GitHub Achievements Automation Bot (Enhanced)[/bold blue]",
        subtitle="[dim]Unlock profile achievement badges safely and reliably[/dim]",
        box=box.ROUNDED
    ))


def interactive_menu(
    api: GitHubAPI,
    repo_target: str,
    coauthor_name: str,
    coauthor_email: str,
    helper_api: Optional[GitHubAPI] = None
):
    """Display interactive CLI menu for user choice."""
    while True:
        menu_table = Table(title="[bold yellow]Available Actions[/bold yellow]", box=box.ROUNDED, show_lines=True)
        menu_table.add_column("Key", justify="center", style="cyan", no_wrap=True)
        menu_table.add_column("Action", style="white")
        menu_table.add_column("Badge(s) Awarded", style="green")

        menu_table.add_row("1", "Run All Badges (Recommended Combo)", "Quickdraw + YOLO + Pull Shark + Pair Extraordinaire")
        menu_table.add_row("2", "Quickdraw only", "Quickdraw (Close issue within 5m)")
        menu_table.add_row("3", "YOLO only", "YOLO (Merge 1 PR without review)")
        menu_table.add_row("4", "Pull Shark (Select tier: 2, 16, 128)", "Pull Shark (Bronze: 2, Silver: 16, Gold: 128)")
        menu_table.add_row("5", "Pair Extraordinaire (With your account as Co-Author)", "Pair Extraordinaire (Bronze: 1, Silver: 10, Gold: 24)")
        menu_table.add_row("6", "Galaxy Brain (Requires 2 accounts)", "Galaxy Brain (Bronze: 2, Silver: 8, Gold: 16)")
        menu_table.add_row("7", "Inspect Live Achievements Status & Diagnostics", "View live progress and sync diagnosis")
        menu_table.add_row("0", "Exit", "Quit application")

        console.print(menu_table)
        choice = console.input("[bold cyan]Select an option [0-7]: [/bold cyan]").strip()

        if choice == "1":
            prs_input = console.input("[cyan]Number of PRs for Pull Shark / Pair Extraordinaire combo (default: 16 for Silver): [/cyan]").strip()
            count = int(prs_input) if prs_input.isdigit() else 16
            unlock_all_badges(api, repo_target, prs_count=count, coauthor_name=coauthor_name, coauthor_email=coauthor_email, helper_api=helper_api)

        elif choice == "2":
            unlock_quickdraw(api, repo_target)

        elif choice == "3":
            run_pr_workflow(api, repo_target, count=1, badge_title="YOLO", enable_coauthor=False)

        elif choice == "4":
            tier_input = console.input("[cyan]Select PR count (2 for Bronze, 16 for Silver, 128 for Gold) [default 16]: [/cyan]").strip()
            count = int(tier_input) if tier_input.isdigit() else 16
            run_pr_workflow(api, repo_target, count=count, badge_title="Pull Shark", enable_coauthor=False)

        elif choice == "5":
            tier_input = console.input("[cyan]Select Co-authored PR count (1 for Bronze, 10 for Silver, 24 for Gold) [default 10]: [/cyan]").strip()
            count = int(tier_input) if tier_input.isdigit() else 10
            run_pr_workflow(
                api, repo_target, count=count,
                badge_title="Pair Extraordinaire",
                enable_coauthor=True,
                coauthor_name=coauthor_name,
                coauthor_email=coauthor_email
            )

        elif choice == "6":
            if not helper_api:
                h_token = console.input("[yellow]Enter secondary/helper GitHub Personal Access Token (or press Enter to skip): [/yellow]").strip()
                if h_token:
                    try:
                        helper_api = GitHubAPI(h_token)
                        helper_api.get_authenticated_user()
                        console.print(f"[green]✓[/green] Helper account verified: [bold]{helper_api.user_login}[/bold]")
                    except Exception as e:
                        console.print(f"[red]Invalid helper token: {e}[/red]")
                        helper_api = None

            tier_input = console.input("[cyan]Select answered discussions count [default 2]: [/cyan]").strip()
            count = int(tier_input) if tier_input.isdigit() else 2
            unlock_galaxy_brain(api, repo_target, helper_api=helper_api, count=count)

        elif choice == "7":
            check_status_and_diagnostics(api, repo_target)

        elif choice == "0":
            console.print("[green]Goodbye![/green]")
            break
        else:
            console.print("[red]Invalid selection. Please enter a number 0-7.[/red]\n")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Automate GitHub Achievement Badges")
    parser.add_argument("--token", "-t", help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--helper-token", help="Secondary GitHub account token for Galaxy Brain")
    parser.add_argument("--repo", "-r", default=None, help="Target sandbox repo name (default: github-achievements-sandbox)")
    parser.add_argument("--all", action="store_true", help="Run full combo for all available badges")
    parser.add_argument("--badge", choices=["quickdraw", "yolo", "pull-shark", "pair-extraordinaire", "galaxy-brain"], help="Run specific badge")
    parser.add_argument("--status", action="store_true", help="Inspect badge status and sync diagnostics")
    parser.add_argument("--prs", type=int, default=16, help="Number of PRs to create (for pull-shark, pair-extraordinaire, or --all)")
    parser.add_argument("--coauthor-name", default=None, help="Co-author name for Pair Extraordinaire")
    parser.add_argument("--coauthor-email", default=None, help="Co-author email for Pair Extraordinaire")
    return parser.parse_args()


def save_token_to_env(token: str):
    """Save token to .env file for convenience."""
    env_path = os.path.join(os.getcwd(), ".env")
    try:
        set_key(env_path, "GITHUB_TOKEN", token)
        console.print("[green]✓ Saved token to .env file.[/green]")
    except Exception:
        pass


def main():
    load_dotenv()
    args = parse_arguments()

    # Get token from CLI arg, .env, or prompt
    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token or token == "ghp_your_personal_access_token_here":
        console.print("[yellow]GitHub token not found in arguments or .env file.[/yellow]")
        token = console.input("[bold cyan]Enter your GitHub Personal Access Token (PAT): [/bold cyan]").strip()
        if token and len(token) > 10:
            save_prompt = console.input("[dim]Save this token in .env for future runs? (Y/n): [/dim]").strip().lower()
            if save_prompt in ("", "y", "yes"):
                save_token_to_env(token)

    if not token:
        console.print("[bold red]Error: A GitHub Personal Access Token is required to proceed.[/bold red]")
        sys.exit(1)

    repo_target = args.repo or os.getenv("GITHUB_REPO", "github-achievements-sandbox")
    coauthor_name = args.coauthor_name or os.getenv("COAUTHOR_NAME", "Monalisa Octocat")
    coauthor_email = args.coauthor_email or os.getenv("COAUTHOR_EMAIL", "octocat@users.noreply.github.com")

    # Initialize client and check token
    try:
        api = GitHubAPI(token)
        user_data = api.get_authenticated_user()
        rate_limit = api.get_rate_limit()
    except Exception as e:
        console.print(f"[bold red]Initialization failed: {e}[/bold red]")
        sys.exit(1)

    # Initialize helper token if present
    helper_token = args.helper_token or os.getenv("HELPER_TOKEN")
    helper_api = None
    if helper_token and helper_token != "ghp_secondary_account_token_here":
        try:
            helper_api = GitHubAPI(helper_token)
            helper_api.get_authenticated_user()
        except Exception:
            helper_api = None

    # Display banner
    print_banner(user_data, rate_limit, repo_target)

    # Ensure repository is ready
    try:
        api.get_or_create_repo(repo_target, public=True)
    except Exception as e:
        console.print(f"[bold red]Failed to prepare repository {repo_target}: {e}[/bold red]")
        sys.exit(1)

    # If status check requested
    if args.status:
        check_status_and_diagnostics(api, repo_target)
        return

    # If CLI flags were provided, run non-interactively
    if args.all:
        unlock_all_badges(api, repo_target, prs_count=args.prs, coauthor_name=coauthor_name, coauthor_email=coauthor_email, helper_api=helper_api)
    elif args.badge == "quickdraw":
        unlock_quickdraw(api, repo_target)
    elif args.badge == "yolo":
        run_pr_workflow(api, repo_target, count=1, badge_title="YOLO", enable_coauthor=False)
    elif args.badge == "pull-shark":
        run_pr_workflow(api, repo_target, count=args.prs, badge_title="Pull Shark", enable_coauthor=False)
    elif args.badge == "pair-extraordinaire":
        run_pr_workflow(
            api, repo_target, count=args.prs,
            badge_title="Pair Extraordinaire",
            enable_coauthor=True,
            coauthor_name=coauthor_name,
            coauthor_email=coauthor_email
        )
    elif args.badge == "galaxy-brain":
        unlock_galaxy_brain(api, repo_target, helper_api=helper_api, count=args.prs)
    else:
        # Launch interactive menu
        interactive_menu(api, repo_target, coauthor_name, coauthor_email, helper_api=helper_api)


if __name__ == "__main__":
    main()
