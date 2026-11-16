import sqlite3
from failingstate.ledger import Ledger

def test_migration_and_lineage(tmp_path):
    path = tmp_path/'ledger.sqlite'
    ledger = Ledger(path)
    run = ledger.start_run('abc')
    base = dict(fingerprint='a', fingerprint_version=1, test_path='test_a.py', test_name='test_a', assertion_source='assert x', exception_type='AssertionError', message='x')
    ledger.record(run, base)
    ledger.record(run, base)
    ledger.finish_run(run, 'failed')
    ledger.db.execute('DROP TABLE lineage')
    ledger.db.execute('PRAGMA user_version=1')
    ledger.db.commit(); ledger.close()
    ledger = Ledger(path)
    assert ledger.db.execute('PRAGMA user_version').fetchone()[0] == 2
    run2 = ledger.start_run('def')
    ledger.record(run2, dict(base, fingerprint='b'))
    assert tuple(ledger.db.execute('SELECT predecessor,successor FROM lineage').fetchone()) == ('a','b')
    assert ledger.db.execute('SELECT count(*) FROM occurrences').fetchone()[0] == 2
    ledger.close()

def test_future_version_rejected(tmp_path):
    path = tmp_path/'future'
    db = sqlite3.connect(path); db.execute('PRAGMA user_version=999'); db.close()
    import pytest
    with pytest.raises(ValueError): Ledger(path)
