# FailingState

[![CI](https://github.com/pooria683/failingstate/actions/workflows/ci.yml/badge.svg)](https://github.com/pooria683/failingstate/actions/workflows/ci.yml) ![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

Your CI has been red for three weeks. Which failures are actually new?
FailingState records pytest failure identities locally in a single SQLite file,
without telemetry or a service. It can give an agent a compact history instead
of another anonymous traceback.

## Quick start

Python 3.11+ and pytest are required. Once published, install into your test
venv with `pip install failingstate` (pytest discovers the plugin there). To
install the CLI separately, use `pipx install failingstate`; the plugin must
also be installed in the environment running pytest. For a checkout, use
`pip install -e .` instead. Add one config file, `pytest.ini`:

```ini
[pytest]
addopts = --fstate
```

Run `pytest` as usual, then `fstate list`, `fstate report --json`, or
`fstate diff --against last-green`. Set `FSTATE_DB` or pass `--fstate-db` to
pytest and `--db` to the CLI to select the same ledger. Keep the ledger between
CI jobs if history should persist. Run from the repository root for Git enrichment; distributed pytest-xdist runs
are not supported. This does not change pytest's exit code: to
suppress recurring-failure alarms, have CI use the diff command's exit code
instead, while still checking for pytest infrastructure errors.

## Example

Illustrative output after a green baseline and two flaky runs (shortened IDs):

```text
$ pytest  # run 1: three failures
$ fstate diff --against last-green
NEW       1280b02a846b tests/test_api.py::test_one
NEW       42f30cd876aa tests/test_api.py::test_two
NEW       5bd40ee19831 tests/test_api.py::test_three
$ pytest  # run 2: the same three and one new failure
$ fstate diff --against last-green
NEW       b4b73711fb3c tests/test_api.py::test_four
RECURRING 1280b02a846b tests/test_api.py::test_one
RECURRING 42f30cd876aa tests/test_api.py::test_two
RECURRING 5bd40ee19831 tests/test_api.py::test_three
$ fstate list
ZOMBIE    f043f4be9e80 tests/test_legacy.py::test_old  count=11 first=2025-06-01T00:00:00+00:00 last=2025-07-01T00:00:00+00:00
$ fstate history test_old
f043f4be9e80... tests/test_legacy.py::test_old count=11 first=... last=...
```

`NEW` means a fingerprint never observed in an earlier run; `RECURRING`
means seen in any earlier run, including before the last green. `FIXED` means
present in the immediately previous completed run but not the latest. A prior
green is required; without one diff exits 2. It exits 1 only for NEW and 0
otherwise. It compares the latest completed run, ignoring interrupted runs;
call it only after a completed pytest run. A zombie is any fingerprint last
seen at least 90 days ago. These are historical labels, not proof of a fix.

## How fingerprinting works

Version 1 hashes compact UTF-8 JSON of `[1, path, test, source, exception,
message]` with SHA-256. Path is relative to pytest's root, with `/` separators;
test is the node ID after the path, including parameters. Source is the failing
statement parsed as Python AST and dumped without location attributes; comments,
spacing and code motion do not matter, while operators and literals do. For
unparseable source, whitespace is collapsed. The exception is its class name.
Message normalization replaces UUIDs, absolute or dot-relative paths, and
hexadecimal addresses, and standalone integers/decimals (including signs) with
`<uuid>`, `<path>`, `<address>`, and `<number>` respectively, then collapses whitespace. Other text and case remain
significant. Thus `assert value == 3 # comment` and `assert value==3` match,
and `expected 17 at /tmp/a` matches `expected 99 at /var/b`; changing `==` to
`!=`, the literal 3 to 4, or `expected` to `actual` changes the hash. Numbers
inside words aren't stripped. Normalization is heuristic and can conflate
meaningful message values; assertion literals are deliberately preserved.

Lineage is a best-effort inference for changed fingerprints on the same test,
not a guaranteed causal tree. Commit SHA identifies the checked-out commit,
not the exact introducing commit, particularly with uncommitted changes. Git
file history and diffs are hints, not causal blame. Reports can contain source,
messages, authors and diffs; review before sharing. Large diffs may be large.

See [the versioned ledger schema](docs/ledger-schema.md). The pytest plugin is
the first release; a Vitest reporter is planned for v0.2, not included here.
A real redacted ledger screenshot is still needed before the launch story can be
published. See [CONTRIBUTING](CONTRIBUTING.md) for normalization governance.
