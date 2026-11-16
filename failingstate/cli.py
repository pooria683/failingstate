import argparse
import json
import sys
from .ledger import Ledger
from .report import age_days, brief

def main(argv=None):
    parser = argparse.ArgumentParser(prog='fstate', description='Local failure history')
    parser.add_argument('--db', default=None, help='ledger path (or FSTATE_DB)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='list known failures')
    h = sub.add_parser('history', help='show inferred test lineage'); h.add_argument('test')
    r = sub.add_parser('report', help='agent-facing failure briefs'); r.add_argument('--json', action='store_true', required=True)
    d = sub.add_parser('diff', help='compare the latest complete run'); d.add_argument('--against', choices=['last-green'], required=True)
    args = parser.parse_args(argv)
    import os
    ledger = Ledger(args.db or os.environ.get('FSTATE_DB', '.failingstate.sqlite3'))
    try:
        if args.command == 'list':
            for row in ledger.summaries():
                state = 'zombie' if age_days(row['last_seen']) >= 90 else ('new' if row['occurrences'] == 1 else 'recurring')
                print(f"{state.upper():9} {row['fingerprint'][:12]} {row['test_path']}::{row['test_name']}  count={row['occurrences']} first={row['first_seen']} last={row['last_seen']}")
        elif args.command == 'report':
            print(json.dumps(brief(ledger), ensure_ascii=False, separators=(',', ':')))
        elif args.command == 'history':
            rows = [r for r in ledger.summaries() if args.test in r['test_path']+'::'+r['test_name']]
            if not rows:
                print('No matching test history.', file=sys.stderr); return 1
            ids = {r['fingerprint'] for r in rows}
            for row in reversed(rows):
                print(f"{row['fingerprint']} {row['test_path']}::{row['test_name']} count={row['occurrences']} first={row['first_seen']} last={row['last_seen']}")
            for edge in ledger.db.execute('SELECT * FROM lineage ORDER BY run_id, predecessor, successor'):
                if edge['predecessor'] in ids or edge['successor'] in ids:
                    print(f"  {edge['predecessor']} -> {edge['successor']} (inferred, run {edge['run_id']})")
        else:
            return diff(ledger)
        return 0
    finally:
        ledger.close()

def diff(ledger):
    db = ledger.db
    latest = db.execute("SELECT * FROM runs WHERE status IN ('green','failed') ORDER BY id DESC LIMIT 1").fetchone()
    if not latest:
        print('No completed runs.', file=sys.stderr); return 2
    green = db.execute("SELECT * FROM runs WHERE status='green' AND id < ? ORDER BY id DESC LIMIT 1", (latest['id'],)).fetchone()
    if not green:
        print('No earlier green run; cannot compare.', file=sys.stderr); return 2
    current = {r[0] for r in db.execute('SELECT fingerprint FROM occurrences WHERE run_id=?', (latest['id'],))}
    # A green run has no failures. Prior observations determine recurrence;
    # fixed compares the preceding completed run to the current run.
    known = {r[0] for r in db.execute('SELECT DISTINCT fingerprint FROM occurrences WHERE run_id < ?', (latest['id'],))}
    previous = db.execute("SELECT id FROM runs WHERE id < ? AND status IN ('green','failed') ORDER BY id DESC LIMIT 1", (latest['id'],)).fetchone()
    prior = {r[0] for r in db.execute('SELECT fingerprint FROM occurrences WHERE run_id=?', (previous[0],))} if previous else set()
    for label, fps in [('NEW', current-known), ('RECURRING', current & known), ('FIXED', prior-current)]:
        for fp in sorted(fps):
            f = db.execute('SELECT test_path,test_name FROM failures WHERE fingerprint=?', (fp,)).fetchone()
            print(f'{label:9} {fp[:12]} {f[0]}::{f[1]}')
    return 1 if current-known else 0

if __name__ == '__main__':
    sys.exit(main())
