from flask import Blueprint, current_app, jsonify, request

from app.errors import TideError
from app.flow import STEPS, calculate, trial_calculate
from app.modules.dredging.trial import run_trial
from app.modules.intake.contract import TRIAL_HEADERS
from app.modules.journal.service import record
from app.modules.proof.service import issue
from app.source import TRIAL_SAMPLES, load_sources

api = Blueprint('api', __name__, url_prefix='/api')


def journal():
    return current_app.extensions['tide_journal']


def trials():
    return current_app.extensions['tide_trials']


@api.route('/stage/<stage>', methods=['GET', 'POST'])
def stage_result(stage):
    payload = request.get_json(silent=True) if request.method == 'POST' else {'sample': request.args.get('sample', 'dirty')}
    sources = load_sources(payload)
    if 'run' in request.args and request.method == 'GET':
        _, _, reports = journal().get(request.args['run'])
    elif set(sources) == set(TRIAL_HEADERS):
        if stage not in STEPS + ('dredging',):
            raise TideError('NO_STAGE', '找不到潮窗模块', 404)
        reports = trial_calculate(sources, stage)
    else:
        if stage not in STEPS:
            raise TideError('NO_STAGE', '找不到潮窗模块', 404)
        reports = calculate(sources, stage)
    return jsonify(reports[stage])


@api.get('/journal')
def list_journal():
    return jsonify(runs=journal().list())


@api.post('/journal')
def publish_journal():
    result = record(journal(), load_sources(request.get_json(silent=True)))
    return jsonify(result), 200 if result['reused'] else 201


@api.get('/journal/<key>')
def inspect_journal(key):
    receipt, _, reports = journal().get(key)
    return jsonify(run_id=key, manifest=receipt, coverage=reports['coverage'])


@api.post('/journal/<key>/rerun')
def repeat_journal(key):
    manifest, sources, _ = journal().get(key)
    return jsonify(record(journal(), sources, manifest))


@api.get('/export/<key>')
def download(key):
    response = jsonify(issue(*journal().get(key)))
    response.headers['Content-Disposition'] = f'attachment; filename="tide-{key[:12]}.json"'
    return response


@api.post('/dredging/trials')
def create_trial():
    sources = load_sources(request.get_json(silent=True))
    if set(sources) != set(TRIAL_HEADERS):
        raise TideError('BAD_SOURCE', '清淤试算须附候选断面表')
    result = run_trial(trials(), sources)
    return jsonify(result), 200 if result['reused'] else 201


@api.get('/dredging/trials')
def list_trials():
    return jsonify(trials=trials().list())


@api.get('/dredging/trials/<key>')
def inspect_trial(key):
    receipt, sources, result = trials().get(key)
    return jsonify(trial_id=key, manifest=receipt, dredging=result)
