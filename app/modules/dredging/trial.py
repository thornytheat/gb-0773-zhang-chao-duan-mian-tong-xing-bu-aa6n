from datetime import UTC, datetime

from app.config import RULES
from app.flow import trial_calculate
from app.modules.intake.contract import TRIAL_HEADERS
from app.modules.journal.manifest import canonical, digest


def trial_manifest(sources):
    inputs = {name: digest(text) for name, text in sources.items()}
    return {'trial_id': digest(canonical([RULES, 'dredging-trial', inputs])), 'inputs': inputs,
            'rule_version': RULES}


def run_trial(store, sources):
    reports = trial_calculate(sources)
    result = reports['dredging']
    receipt = trial_manifest(sources)
    receipt['started_at'] = datetime.now(UTC).isoformat(timespec='seconds')
    receipt['result_sha256'] = digest(canonical(result))
    created = store.publish(receipt, sources, result)
    return {'trial_id': receipt['trial_id'], 'manifest': receipt, 'reused': not created, 'result': result}
