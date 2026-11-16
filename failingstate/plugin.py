"""Opt-in pytest plugin. Enable with --fstate or [pytest] addopts = --fstate."""
import os
from pathlib import Path
import pytest
from . import git
from .fingerprint import fingerprint, FINGERPRINT_VERSION
from .ledger import Ledger


def pytest_addoption(parser):
    group = parser.getgroup('failingstate')
    group.addoption('--fstate', action='store_true', help='record failures in the local FailingState ledger')
    group.addoption('--fstate-db', default=os.environ.get('FSTATE_DB', '.failingstate.sqlite3'), help='ledger path')


def pytest_configure(config):
    if config.getoption('--fstate') and not hasattr(config, 'workerinput'):
        plugin = Recorder(config)
        config.pluginmanager.register(plugin, 'failingstate-recorder')

class Recorder:
    def __init__(self, config):
        self.root = Path(str(config.rootpath))
        self.ledger = Ledger(config.getoption('--fstate-db'))
        self.sha = git.commit()
        self.run = self.ledger.start_run(self.sha)
        self.failed = False
        self.collection_failed = False

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if not report.failed or call.excinfo is None:
            return
        self.failed = True
        exc = call.excinfo
        # Prefer the last frame in the test file; it identifies the actual
        # assertion even when the test has moved within the file.
        frames = [e for e in exc.traceback if Path(str(e.path)) == Path(str(item.path))]
        entry = frames[-1] if frames else exc.traceback[-1]
        try:
            source = str(entry.statement).strip()
        except Exception:
            source = ''
        path = os.path.relpath(str(item.path), str(self.root)).replace(os.sep, '/')
        name = item.nodeid.split('::', 1)[-1]
        typ = exc.type.__name__
        message = str(exc.value)
        fp = fingerprint(path, name, source, typ, message)
        blame_sha, title, author = git.blame(self.sha, path)
        self.ledger.record(self.run, dict(fingerprint=fp, fingerprint_version=FINGERPRINT_VERSION, test_path=path, test_name=name, assertion_source=source, exception_type=typ, message=message, commit_sha=self.sha, blame_sha=blame_sha, blame_title=title, blame_author=author))

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_failed = True

    def pytest_sessionfinish(self, session, exitstatus):
        # Collection errors, no tests, and interrupted runs cannot establish a green baseline.
        status = 'green' if exitstatus == 0 and not self.failed and not self.collection_failed else ('failed' if exitstatus == 1 and not self.collection_failed else 'interrupted')
        self.ledger.finish_run(self.run, status)
        self.ledger.close()
