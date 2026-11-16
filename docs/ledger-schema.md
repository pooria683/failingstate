# Ledger schema (SQLite, version 2)

`PRAGMA user_version` is the schema version; unknown newer versions are rejected.
Versions 1 and 2 are supported: migration 1 → 2 adds `lineage` without changing
existing records. SQLite foreign keys are enabled by the writer. Timestamps are
UTC ISO 8601 strings; IDs are monotonically increasing local integers. A ledger
is local to one repository/test root. Copy the SQLite file when sharing it;
there is no server or telemetry.

* `runs(id, started_at, finished_at, commit_sha, status)`: one row per pytest
  session; status is `running`, `green`, `failed`, or `interrupted`. A run is
  finalized once, not deleted. A process crash can leave it `running`.
* `failures(fingerprint, fingerprint_version, test_path, test_name,
  assertion_source, exception_type, message)`: immutable identity and first
  observed details. Fingerprint is a lowercase SHA-256 hex string.
* `occurrences(id, run_id, fingerprint, seen_at, commit_sha, blame_sha,
  blame_title, blame_author)`: one observation per fingerprint per run,
  unique on `(run_id, fingerprint)`. SHA is HEAD at session start, not proof
  that the commit introduced the failure; dirty working trees are possible.
  Blame fields describe the last commit touching the test file at that SHA,
  not necessarily the cause. Git metadata can be null.
* `lineage(predecessor, successor, run_id)`: inferred directed edges between
  different fingerprints observed for the same test in successive observed
  runs. Primary key `(predecessor, successor)`. Inference can be wrong when a
  test has multiple independent assertions or fluctuates; edges can form cycles.

First/last seen and occurrence counts are derived from occurrences. Apart from
run finalization and additive migrations, records are append-only. Writers
must implement the fingerprint version rules and preserve the uniqueness and
foreign-key constraints, and must not claim a green run if collection or the
session failed. Interoperability does not imply that different languages share
fingerprints: v1 source normalization is Python-specific.
