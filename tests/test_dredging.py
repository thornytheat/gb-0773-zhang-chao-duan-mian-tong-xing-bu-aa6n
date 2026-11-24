from fractions import Fraction

import pytest

from app.errors import TideError
from app.flow import trial_calculate
from app.modules.dredging.clock import DredgingClock
from app.modules.dredging.service import evaluate, parse_plans, tide_groups
from app.modules.dredging.store import TrialStore
from app.modules.dredging.trial import run_trial
from app.source import load_sources


@pytest.fixture
def trial_sources():
    return load_sources({'sample': 'tide2'})


@pytest.fixture
def trial_reports(trial_sources):
    return trial_calculate(trial_sources)


def test_baseline_two_tides(trial_reports):
    plan = trial_reports['dredging']
    assert [t['released'] for t in plan['baseline']['tides']] == [3, 3]
    assert [t['total'] for t in plan['baseline']['tides']] == [4, 4]
    assert plan['baseline']['total_released'] == 6


def test_early_closure_blocks_current_tide(trial_reports):
    plan = evaluate(trial_reports['readings'], trial_reports['datum'],
                    trial_reports['readings']['tables']['dredging'])
    early = next(row for row in plan['candidates'] if row['candidate'] == '浅滩早班')
    assert [t['released'] for t in early['tides']] == [1, 4]
    assert early['delta'] == -1


def test_late_work_recommended(trial_reports):
    plan = evaluate(trial_reports['readings'], trial_reports['datum'],
                    trial_reports['readings']['tables']['dredging'])
    late = next(row for row in plan['candidates'] if row['candidate'] == '浅滩晚班')
    assert late['recommended'] is True and late['delta'] == 1
    assert plan['recommended'] == '浅滩晚班'


def test_gain_only_after_completion():
    section = {'offset_s': 0, 'gap_s': 600,
               'points': [{'time': 0, 'depth_m': '2.4', 'line': 1},
                          {'time': 900, 'depth_m': '2.4', 'line': 2}],
               'bands': [{'start': 0, 'end': 900, 'code': 'LINEAR', 'crossing': None,
                          'depths_m': ['2.4', '2.4'], 'lines': [1, 2]}]}
    threshold = Fraction('2.5')
    plan = {'start': 100, 'work_s': 600, 'gain_m': Fraction('0.3')}
    clock = DredgingClock('浅滩', section, plan)
    assert clock.at(200, threshold)['code'] == 'DREDGING_CLOSED'
    assert clock.at(50, threshold)['status'] == 'blocked'
    finished = clock.at(800, threshold)
    assert finished['status'] == 'open' and finished['depth_m'] == '27/10'


def test_unknown_stays_unknown_after_gain():
    section = {'offset_s': 0, 'gap_s': 600,
               'points': [{'time': 0, 'depth_m': '2.4', 'line': 1},
                          {'time': 900, 'depth_m': '2.4', 'line': 2}],
               'bands': [{'start': 0, 'end': 900, 'code': 'OVER_GAP', 'crossing': None,
                          'depths_m': ['2.4', '2.4'], 'lines': [1, 2]}]}
    clock = DredgingClock('浅滩', section, {'start': 0, 'work_s': 10, 'gain_m': Fraction('0.3')})
    assert clock.at(500, Fraction('2.5'))['status'] == 'unknown'


def test_missing_evidence_not_filled_by_gain():
    reports = trial_calculate(load_sources({'sample': 'tide2_dirty'}))
    plan = reports['dredging']
    late = next(row for row in plan['candidates'] if row['candidate'] == '浅滩晚班')
    assert late['tides'][1]['released'] == 3
    blocked_ship = next(s for s in late['tides'][1]['ships'] if s['vessel'] == '赶潮99')
    assert blocked_ship['releasable'] is False


def test_tide_groups_keep_overlap(trial_reports):
    orders = {k: v['order'] for k, v in trial_reports['windows'].items()}
    groups = tide_groups(orders)
    assert len(groups) == 2 and {len(g) for g in groups} == {4}


def test_bad_candidate_rejected(trial_reports):
    rows = [{'line': 9, 'raw': {'candidate': 'x', 'section': '幽灵断面',
                                'start_at': '2026-11-22T23:30:00+08:00', 'work_s': '600', 'gain_m': '0.3'}}]
    with pytest.raises(TideError) as error:
        parse_plans(rows, trial_reports['datum']['sections'])
    assert error.value.code == 'BAD_DREDGING'


def test_trial_persists_once(tmp_path, trial_sources):
    store = TrialStore(tmp_path / 'trials.sqlite3')
    first = run_trial(store, trial_sources)
    second = run_trial(store, trial_sources)
    assert first['trial_id'] == second['trial_id']
    assert first['reused'] is False and second['reused'] is True
    assert len(store.list()) == 1


def test_failed_trial_leaves_no_archive(tmp_path):
    store = TrialStore(tmp_path / 'trials.sqlite3')
    bad = {name: 'bad,header\nx\n' for name in ('observations', 'stations', 'vessels', 'dredging')}
    with pytest.raises(TideError):
        run_trial(store, bad)
    assert store.list() == []


def test_trial_api_create_and_reuse(client):
    response = client.post('/api/dredging/trials', json={'sample': 'tide2'})
    assert response.status_code == 201
    again = client.post('/api/dredging/trials', json={'sample': 'tide2'})
    assert again.status_code == 200 and again.json['reused'] is True
    assert len(client.get('/api/dredging/trials').json['trials']) == 1


def test_trial_api_requires_four_sources(client, sources):
    response = client.post('/api/dredging/trials', json={'sources': sources})
    assert (response.status_code, response.json['code']) == (422, 'BAD_SOURCE')


def test_dredging_page_renders(client):
    page = client.get('/desk/dredging?sample=tide2')
    text = page.get_data(as_text=True)
    assert page.status_code == 200 and '清淤候选试算' in text and '现状两潮对照' in text


def test_dredging_page_without_candidates_shows_baseline(client):
    page = client.get('/desk/dredging?sample=dirty')
    text = page.get_data(as_text=True)
    assert page.status_code == 200 and '现状两潮对照' in text and '无可用候选' in text


def test_stage_api_serves_dredging(client):
    response = client.get('/api/stage/dredging?sample=tide2')
    assert response.status_code == 200
    assert response.json['recommended'] == '浅滩晚班'
