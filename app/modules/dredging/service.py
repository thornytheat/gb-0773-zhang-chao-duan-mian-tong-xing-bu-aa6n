from fractions import Fraction

from app.clock import depth, moment
from app.errors import TideError
from app.modules.crossings.service import find_crossings
from app.modules.passage.service import route_windows
from app.modules.passage.state import SectionClock
from app.modules.schedule.orders import orders

from .clock import DredgingClock
from .contract import DREDGING_SOURCE


def parse_plans(rows, sections):
    plans, seen = [], set()
    for record in rows:
        raw = record['raw']
        name = raw['candidate'].strip()
        section = raw['section'].strip()
        try:
            start = moment(raw['start_at'])
            work = int(raw['work_s'])
            gain = depth(raw['gain_m'])
            if not name or name in seen or section not in sections or work <= 0 or work > 7 * 86400 or gain <= 0:
                raise ValueError()
        except (ValueError, OverflowError) as exc:
            raise TideError('BAD_DREDGING', f'清淤候选第 {record["line"]} 行定义错误') from exc
        seen.add(name)
        plans.append(dict(candidate=name, section=section, start=start, work_s=work, gain_m=gain, line=record['line']))
    return plans


def tide_groups(vessel_orders):
    """按船期出发窗口的重叠关系归潮，互不相接者另算一潮。"""
    ordered = sorted(vessel_orders.values(), key=lambda o: (o['start'], o['end']))
    groups, current = [], []
    for order in ordered:
        if current and order['start'] <= current_end(current):
            current.append(order)
        else:
            if current:
                groups.append(current)
            current = [order]
    if current:
        groups.append(current)
    return groups


def current_end(group):
    return max(order['end'] for order in group)


def releasable(route):
    return bool(route['windows']) or bool(route['isolated_points'])


def simulate(crossings, groups, plan):
    if plan is None:
        routes = route_windows(crossings)
    else:
        def factory(name, section, plan=plan):
            if name == plan['section']:
                return DredgingClock(name, section, plan)
            return SectionClock(name, section)

        routes = route_windows(crossings, factory)
    tides, total = [], 0
    for index, group in enumerate(groups, start=1):
        ships = []
        for order in group:
            ok = releasable(routes[order['vessel']])
            ships.append(dict(vessel=order['vessel'], releasable=ok))
            total += ok
        tides.append(dict(tide=index, start=min(o['start'] for o in group), end=current_end(group),
                          ships=ships, released=sum(1 for row in ships if row['releasable']),
                          total=len(ships)))
    return tides, total


def evaluate(readings, normalized, candidate_rows):
    vessel_orders = orders(readings)
    plans = parse_plans(candidate_rows, normalized['sections'])
    crossings = find_crossings(normalized, vessel_orders)
    groups = tide_groups(vessel_orders)
    baseline_tides, baseline_total = simulate(crossings, groups, None)
    candidates = []
    for plan in plans:
        tides, total = simulate(crossings, groups, plan)
        candidates.append(dict(
            candidate=plan['candidate'], section=plan['section'], line=plan['line'],
            start=plan['start'], work_s=plan['work_s'],
            gain_m=str(plan['gain_m']), tides=tides, total_released=total,
            delta=total - baseline_total))
    if candidates:
        best = max(candidates, key=lambda row: (row['total_released'],
                                                row['tides'][-1]['released'], -row['start'], row['candidate']))
        for row in candidates:
            row['recommended'] = row is best
    return {'source': DREDGING_SOURCE, 'baseline': {'tides': baseline_tides, 'total_released': baseline_total},
            'candidates': candidates,
            'recommended': next((row['candidate'] for row in candidates if row['recommended']), None)}
