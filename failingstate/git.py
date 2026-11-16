"""Best-effort git enrichment; no network access."""
import subprocess

def git(*args):
    try:
        result = subprocess.run(['git', *args], capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None

def commit():
    return git('rev-parse', 'HEAD')

def blame(sha, path):
    if not sha:
        return (None, None, None)
    result = git('log', '-1', '--format=%H%x00%s%x00%an', sha, '--', path)
    parts = result.split('\0') if result else []
    return tuple(parts) if len(parts) == 3 else (None, None, None)

def last_diff(sha, path):
    if not sha:
        return None
    change = git('log', '-1', '--format=%H', sha, '--', path)
    return git('show', '--format=', '--no-ext-diff', '--no-color', change, '--', path) if change else None
