from fractions import Fraction

from flask import Blueprint, render_template, request

from app.api import journal, trials
from app.clock import instant
from app.config import RULES
from app.errors import TideError
from app.flow import calculate, trial_calculate
from app.modules.dredging.service import evaluate
from app.modules.proof.service import issue
from app.reasons import REASONS
from app.modules.intake.contract import HEADERS
from app.source import TRIAL_SAMPLES, load_sources

web = Blueprint('tide_desk', __name__)
CHAPTERS = {'coverage': '船期覆盖勾稽', 'dredging': '清淤安排', 'readings': '潮尺读数采信',
            'datum': '站点基准统一', 'crossings': '水位阈值交点', 'windows': '全程可行潮窗',
            'journal': '运行留档', 'proof': '潮窗证据签发'}
TRIAL_CHAPTERS = frozenset({'dredging'})
STATES = {'open': '可行', 'blocked': '不可行', 'unknown': '缺证'}
SAMPLE_LABELS = {'dirty': '断测场次', 'clean': '连续测站', 'tide2': '两潮连续', 'tide2_dirty': '两潮断测'}


@web.get('/')
@web.get('/desk/<chapter>')
def desk(chapter='coverage'):
    if chapter not in CHAPTERS:
        raise TideError('NO_STAGE', '找不到潮窗模块', 404)
    sample = request.args.get('sample', 'dirty')
    key = request.args.get('run')
    trial_key = request.args.get('trial')
    proof = None
    history, trial_history = [], []
    if trial_key:
        receipt, sources, dredging = trials().get(trial_key)
        reports = trial_calculate(sources)
        receipt_run = None
        trial_history = trials().list()
    elif key or chapter in ('journal', 'proof'):
        key = key or journal_record(sample)
        receipt_run, sources, reports = journal().get(key)
        receipt = None
        history = journal().list()
    else:
        sources = load_sources({'sample': sample})
        if chapter in TRIAL_CHAPTERS:
            reports = trial_calculate(sources) if sample in TRIAL_SAMPLES else calculate(sources)
            if 'dredging' not in reports:
                reports['dredging'] = evaluate(reports['readings'], reports['datum'], [])
        else:
            reports = trial_calculate(sources) if sample in TRIAL_SAMPLES else calculate(sources)
        receipt, receipt_run = None, None
    vessel = request.args.get('vessel', next(iter(reports['coverage']['ships'])))
    if vessel not in reports['coverage']['ships']:
        raise TideError('NO_VESSEL', '找不到该船期', 404)
    if chapter == 'proof':
        proof = issue(receipt_run, sources, reports)
    return render_template('base.html', chapter=chapter, chapters=CHAPTERS, states=STATES, sample=sample,
                           sample_labels=SAMPLE_LABELS, receipt=receipt_run, key=key, trial_key=trial_key,
                           trial_available=sample in TRIAL_SAMPLES,
                           reports=reports, vessel=vessel, reason=REASONS,
                           gauge_fill=min(100, float(Fraction(reports['windows'][vessel]['order']['threshold_m'])) * 25),
                           seal=proof['seal_sha256'] if proof else None, time=instant, rule=RULES,
                           history=history, trial_history=trial_history)


def journal_record(sample):
    from app.modules.journal.service import record
    sources = load_sources({'sample': sample})
    sources = {name: text for name, text in sources.items() if name in HEADERS}
    return record(journal(), sources)['run_id']
