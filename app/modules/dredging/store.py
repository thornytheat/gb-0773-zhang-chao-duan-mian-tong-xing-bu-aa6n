import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from app.errors import TideError


class TrialStore:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS dredging_trials (
                id TEXT PRIMARY KEY, created TEXT NOT NULL, receipt TEXT NOT NULL,
                inputs TEXT NOT NULL, result TEXT NOT NULL)''')

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            yield connection

    def publish(self, receipt, sources, result):
        with self.connection() as connection:
            cursor = connection.execute(
                'INSERT INTO dredging_trials VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING',
                (receipt['trial_id'], receipt['started_at'],
                 json.dumps(receipt, ensure_ascii=False, sort_keys=True),
                 json.dumps(sources, ensure_ascii=False, sort_keys=True),
                 json.dumps(result, ensure_ascii=False, sort_keys=True)))
            return cursor.rowcount == 1

    def get(self, key):
        with self.connection() as connection:
            row = connection.execute(
                'SELECT receipt, inputs, result FROM dredging_trials WHERE id=?', (key,)).fetchone()
        if row is None:
            raise TideError('NO_TRIAL', '未找到这份清淤试算', 404)
        return tuple(json.loads(value) for value in row)

    def list(self):
        with self.connection() as connection:
            rows = connection.execute(
                'SELECT receipt FROM dredging_trials ORDER BY created DESC, id LIMIT 40').fetchall()
        return [json.loads(row[0]) for row in rows]
