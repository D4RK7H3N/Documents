import shlex
import subprocess

from django.conf import settings

from .git_repo import minimal_env


def run_opencode(worktree, prompt_text):
    """Run the OpenCode CLI in the worktree with a minimal environment."""
    command = [settings.OPENCODE_BIN, "run"]
    if settings.OPENCODE_MODEL:
        command += ["--model", settings.OPENCODE_MODEL]
    if settings.OPENCODE_EXTRA_ARGS:
        command += shlex.split(settings.OPENCODE_EXTRA_ARGS)

    completed = subprocess.run(
        command,
        cwd=str(worktree),
        env=minimal_env(),
        input=prompt_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=settings.OPENCODE_TIMEOUT,
    )
    output = completed.stdout or ""
    header = f"--- opencode: {' '.join(command)} ---\n"
    if completed.returncode != 0:
        raise RuntimeError(f"opencode exited {completed.returncode}:\n{output[-2000:]}")
    return header + output


def run_tests(worktree, test_command):
    """Run the project's trusted test command in the worktree."""
    completed = subprocess.run(
        test_command,
        shell=True,
        cwd=str(worktree),
        env=minimal_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=settings.TEST_TIMEOUT,
    )
    output = completed.stdout or ""
    if completed.returncode != 0:
        raise RuntimeError(f"Tests failed (exit {completed.returncode}):\n{output[-2000:]}")
    return "--- tests ---\n" + output
