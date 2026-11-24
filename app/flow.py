from app.modules.crossings.service import find_crossings
from app.modules.datum.service import normalize
from app.modules.intake.service import intake
from app.modules.passage.service import route_windows
from app.modules.schedule.orders import orders
from app.modules.schedule.service import reconcile

STEPS = ('readings', 'datum', 'crossings', 'windows', 'coverage')


def calculate(inputs, stop='coverage'):
    reports = {'readings': intake(inputs)}
    if stop == 'readings':
        return reports
    reports['datum'] = normalize(reports['readings'])
    if stop == 'datum':
        return reports
    reports['crossings'] = find_crossings(reports['datum'], orders(reports['readings']))
    if stop == 'crossings':
        return reports
    reports['windows'] = route_windows(reports['crossings'])
    if stop == 'windows':
        return reports
    reports['coverage'] = reconcile(reports['windows'])
    return reports


def trial_calculate(inputs, stop='dredging'):
    from app.modules.dredging.service import evaluate
    from app.modules.intake.contract import TRIAL_HEADERS

    reports = {'readings': intake(inputs, TRIAL_HEADERS)}
    if stop == 'readings':
        return reports
    reports['datum'] = normalize(reports['readings'])
    if stop == 'datum':
        return reports
    reports['crossings'] = find_crossings(reports['datum'], orders(reports['readings']))
    if stop == 'crossings':
        return reports
    reports['windows'] = route_windows(reports['crossings'])
    if stop == 'windows':
        return reports
    reports['coverage'] = reconcile(reports['windows'])
    if stop == 'coverage':
        return reports
    reports['dredging'] = evaluate(reports['readings'], reports['datum'],
                                   reports['readings']['tables']['dredging'])
    return reports
