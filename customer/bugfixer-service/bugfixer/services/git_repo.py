import base64
import os
import re
import shutil
import subprocess
from pathlib import Path

from django.conf import settings


class GitError(RuntimeError):
    pass


def _run(args, cwd=None, env=None, timeout=300, check=True):
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = proc.stdout or ""
    if check and proc.returncode != 0:
        displayed = [
            "http.extraheader=[REDACTED]" if str(a).startswith("http.extraheader=") else str(a)
            for a in args[:4]
        ]
        raise GitError(f"Command failed: {' '.join(displayed)}...\n{output[-2000:]}")
    return output


def minimal_env():
    """Only PATH, HOME and the explicitly configured variables reach subprocesses."""
    env = {}
    for name in ("PATH", "HOME") + tuple(settings.WORKER_ENV_ALLOWLIST):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def gh_env():
    env = minimal_env()
    if settings.GITHUB_TOKEN:
        env["GH_TOKEN"] = settings.GITHUB_TOKEN
    return env


def _auth_args():
    """Auth as a transient git option so credentials never enter .git/config."""
    token = settings.GITHUB_TOKEN
    if not token:
        return []
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]


def owner_repo(repo_url):
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$", repo_url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def mirror_path(project):
    return settings.WORKDIR / "repos" / str(project.pk)


def worktree_path(report_id):
    return settings.WORKDIR / "worktrees" / f"report-{report_id}"


def ensure_mirror(project):
    path = mirror_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not (path / "HEAD").exists():
        _run(["git"] + _auth_args() + ["clone", "--bare", project.repo_url, str(path)], timeout=600)
    else:
        _run(["git"] + _auth_args() + ["-C", str(path), "fetch", "--prune", "origin"], timeout=600)
    return path


def add_worktree(project, report):
    """Create an isolated worktree on a new fix branch from origin/<base_branch>."""
    mirror = ensure_mirror(project)
    branch = f"fix/report-{report.pk}"
    worktree = worktree_path(report.pk)
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
    _run(["git", "-C", str(mirror), "worktree", "prune"], check=False)
    _run(["git", "-C", str(mirror), "branch", "-D", branch], check=False)
    _run(
        ["git", "-C", str(mirror), "worktree", "add", "-b", branch, str(worktree), f"refs/heads/{project.base_branch}"],
        timeout=600,
    )
    return worktree, branch


def changed_files(worktree):
    output = _run(["git", "-C", str(worktree), "status", "--porcelain"])
    paths = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path:
            paths.append(path)

    total = 0
    for path in paths:
        candidate = Path(worktree) / path
        if candidate.is_file():
            total += candidate.stat().st_size
    if total > settings.MAX_DIFF_BYTES:
        raise GitError(f"Diff too large: {total} bytes (limit {settings.MAX_DIFF_BYTES}).")
    return paths


def commit_and_push(project, report, worktree, branch):
    _run(["git", "-C", str(worktree), "add", "-A"])
    _run(
        [
            "git",
            "-C",
            str(worktree),
            "-c",
            "user.name=BugFixer",
            "-c",
            "user.email=bugfixer@localhost",
            "commit",
            "-m",
            f"fix: automated fix for report #{report.pk}",
        ]
    )
    _run(
        ["git"] + _auth_args() + ["-C", str(worktree), "push", "--force", project.repo_url, f"HEAD:refs/heads/{branch}"],
        timeout=600,
    )


def create_pull_request(project, report):
    """Create a PR for an already-pushed branch (used by auto_pr and admin approval)."""
    repo = owner_repo(project.repo_url)
    if not repo:
        raise GitError("Cannot determine GitHub owner/repo from repo_url.")
    output = _run(
        [
            "gh", "pr", "create",
            "--repo", repo,
            "--head", report.branch,
            "--base", project.base_branch,
            "--title", f"Fix: automated fix for report #{report.pk}",
            "--body", f"Automated fix for bug report #{report.pk}.\n\n{report.message[:1000]}",
        ],
        cwd=str(mirror_path(project)),
        env=gh_env(),
        timeout=180,
    )
    urls = [line.strip() for line in output.splitlines() if line.strip().startswith("http")]
    if not urls:
        raise GitError(f"gh pr create produced no URL: {output[-500:]}")
    return urls[-1]


def remove_worktree(report_id, project=None):
    worktree = worktree_path(report_id)
    mirror = mirror_path(project) if project else None
    if mirror and (mirror / "HEAD").exists():
        _run(["git", "-C", str(mirror), "worktree", "remove", "--force", str(worktree)], check=False)
        _run(["git", "-C", str(mirror), "branch", "-D", f"fix/report-{report_id}"], check=False)
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
