from bisect import bisect_right
from fractions import Fraction

from app.modules.passage.state import SectionClock


class DredgingClock(SectionClock):
    """封航期间一律不可行；完工后按增深量整体加深，缺测照旧缺证。"""

    def __init__(self, name, section, plan):
        super().__init__(name, section)
        self.closure_start = plan['start']
        self.closure_end = plan['start'] + plan['work_s']
        self.gain = plan['gain_m']

    def at(self, departure, threshold):
        local = departure + self.offset
        if self.closure_start <= local < self.closure_end:
            return {'section': self.name, 'at': str(local), 'depth_m': None, 'lines': [],
                    'code': 'DREDGING_CLOSED', 'status': 'blocked'}
        detail = super().at(departure, threshold)
        if detail['status'] == 'unknown' or local < self.closure_end:
            return detail
        index = bisect_right(self.times, local) - 1
        if index < 0:
            return detail
        value = Fraction(detail['depth_m']) + self.gain
        return {**detail, 'depth_m': str(value),
                'status': 'open' if value >= threshold else 'blocked',
                'code': 'DEPTH_OK' if value >= threshold else 'UNDER_DEPTH'}
