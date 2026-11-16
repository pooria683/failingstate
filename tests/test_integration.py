import os
from pathlib import Path
import subprocess
import sys

ROOT = str(Path(__file__).resolve().parents[1])

def test_flaky_ci_workflow(tmp_path):
    def run(*args):
        env = dict(os.environ, PYTHONPATH=ROOT, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        return subprocess.run(args, cwd=tmp_path, env=env, text=True, capture_output=True)
    def git(*args):
        assert run('git', *args).returncode == 0
    git('init'); git('config', 'user.email', 'test@example.com'); git('config', 'user.name', 'Test')
    (tmp_path/'test_flaky.py').write_text('import os\ndef test_old():\n    assert not os.getenv("OLD")\ndef test_new():\n    assert not os.getenv("NEW")\n')
    git('add', 'test_flaky.py'); git('commit', '-m', 'add tests')
    def pytest_run(old=False, new=False):
        env = dict(os.environ, PYTHONPATH=ROOT, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        if old: env['OLD']='1'
        if new: env['NEW']='1'
        return subprocess.run([sys.executable, '-m', 'pytest', '-p', 'failingstate.plugin', '--fstate', '-q'], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert pytest_run().returncode == 0
    assert pytest_run(old=True).returncode == 1
    d = run(sys.executable, '-m', 'failingstate.cli', 'diff', '--against', 'last-green')
    assert d.returncode == 1 and 'NEW' in d.stdout
    assert pytest_run(old=True, new=True).returncode == 1
    d = run(sys.executable, '-m', 'failingstate.cli', 'diff', '--against', 'last-green')
    assert d.returncode == 1 and 'RECURRING' in d.stdout and 'NEW' in d.stdout
    assert pytest_run(old=True).returncode == 1
    d = run(sys.executable, '-m', 'failingstate.cli', 'diff', '--against', 'last-green')
    assert d.returncode == 0 and 'RECURRING' in d.stdout and 'FIXED' in d.stdout
    import json
    report = json.loads(run(sys.executable, '-m', 'failingstate.cli', 'report', '--json').stdout)
    assert len(report) == 2 and any(x['suspicious_commits'][0]['blame_title'] == 'add tests' for x in report)
