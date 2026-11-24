OBSERVATION = ('station', 'observed_at', 'level', 'unit', 'quality')
STATION = ('station', 'section', 'datum_m', 'bed_m', 'priority', 'offset_s', 'gap_s')
VESSEL = ('vessel', 'draft_m', 'clearance_m', 'start', 'end', 'requested')
DREDGING = ('candidate', 'section', 'start_at', 'work_s', 'gain_m')
HEADERS = {'observations': OBSERVATION, 'stations': STATION, 'vessels': VESSEL}
TRIAL_HEADERS = {**HEADERS, 'dredging': DREDGING}
SENTINELS = frozenset({'', '-', 'N/A', 'NULL', '未知'})
