from datetime import datetime, timezone
from . import git

def age_days(value):
    return max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(value)).days)

def brief(ledger):
    result = []
    for row in ledger.summaries():
        last = ledger.db.execute('SELECT * FROM occurrences WHERE fingerprint=? ORDER BY id DESC LIMIT 1', (row['fingerprint'],)).fetchone()
        commits = ledger.db.execute('''SELECT DISTINCT commit_sha, blame_sha, blame_title, blame_author FROM occurrences WHERE fingerprint=? ORDER BY id DESC LIMIT 5''', (row['fingerprint'],)).fetchall()
        result.append({'fingerprint': row['fingerprint'], 'test': row['test_path']+'::'+row['test_name'], 'first_seen': row['first_seen'], 'last_seen': row['last_seen'], 'age_days': age_days(row['first_seen']), 'recurrences': row['occurrences']-1, 'suspicious_commits': [dict(c) for c in commits], 'last_diff': git.last_diff(last['commit_sha'], row['test_path'])})
    return result
