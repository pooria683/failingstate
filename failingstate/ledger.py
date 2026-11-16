"""SQLite ledger. Run and occurrence records are never updated or deleted."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 2

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Ledger:
    def __init__(self, path='.failingstate.sqlite3'):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.migrate()

    def migrate(self):
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            raise ValueError(f'Unsupported ledger schema {version}; maximum is {SCHEMA_VERSION}')
        with self.db:
            if version < 1:
                self.db.executescript('''
                CREATE TABLE runs (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, commit_sha TEXT, status TEXT NOT NULL CHECK(status IN ('running','green','failed','interrupted')));
                CREATE TABLE failures (fingerprint TEXT PRIMARY KEY, fingerprint_version INTEGER NOT NULL, test_path TEXT NOT NULL, test_name TEXT NOT NULL, assertion_source TEXT NOT NULL, exception_type TEXT NOT NULL, message TEXT NOT NULL);
                CREATE TABLE occurrences (id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES runs(id), fingerprint TEXT NOT NULL REFERENCES failures(fingerprint), seen_at TEXT NOT NULL, commit_sha TEXT, blame_sha TEXT, blame_title TEXT, blame_author TEXT, UNIQUE(run_id, fingerprint));
                CREATE INDEX occurrences_fingerprint ON occurrences(fingerprint, run_id);
                PRAGMA user_version=1;
                ''')
            if version < 2:
                self.db.executescript('''
                CREATE TABLE lineage (predecessor TEXT NOT NULL REFERENCES failures(fingerprint), successor TEXT NOT NULL REFERENCES failures(fingerprint), run_id INTEGER NOT NULL REFERENCES runs(id), PRIMARY KEY(predecessor, successor), CHECK(predecessor != successor));
                PRAGMA user_version=2;
                ''')

    def start_run(self, sha):
        with self.db:
            return self.db.execute("INSERT INTO runs(started_at,commit_sha,status) VALUES(?,?,'running')", (now(), sha)).lastrowid

    def finish_run(self, run_id, status):
        if status not in ('green', 'failed', 'interrupted'):
            raise ValueError(status)
        with self.db:
            self.db.execute('UPDATE runs SET finished_at=?, status=? WHERE id=?', (now(), status, run_id))

    def record(self, run_id, data):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO failures VALUES(?,?,?,?,?,?,?)', tuple(data[k] for k in ('fingerprint','fingerprint_version','test_path','test_name','assertion_source','exception_type','message')))
            # Only infer a successor when the immediately preceding observation for
            # this test was a different fingerprint. Multiple failures in one run
            # are not assumed to be mutations of one another.
            previous = self.db.execute('''SELECT o.fingerprint FROM occurrences o JOIN failures f ON f.fingerprint=o.fingerprint
                WHERE f.test_path=? AND f.test_name=? AND o.run_id < ? ORDER BY o.run_id DESC, o.id DESC LIMIT 1''', (data['test_path'], data['test_name'], run_id)).fetchone()
            self.db.execute('''INSERT OR IGNORE INTO occurrences(run_id,fingerprint,seen_at,commit_sha,blame_sha,blame_title,blame_author) VALUES(?,?,?,?,?,?,?)''',
                (run_id,data['fingerprint'],now(),data.get('commit_sha'),data.get('blame_sha'),data.get('blame_title'),data.get('blame_author')))
            if previous and previous[0] != data['fingerprint']:
                self.db.execute('INSERT OR IGNORE INTO lineage VALUES(?,?,?)', (previous[0], data['fingerprint'], run_id))

    def summaries(self):
        return self.db.execute('''SELECT f.*, MIN(o.seen_at) first_seen, MAX(o.seen_at) last_seen, COUNT(o.id) occurrences,
            MIN(o.run_id) first_run, MAX(o.run_id) last_run FROM failures f JOIN occurrences o USING(fingerprint)
            GROUP BY f.fingerprint ORDER BY first_seen DESC, occurrences DESC, f.fingerprint''').fetchall()

    def close(self):
        self.db.close()
