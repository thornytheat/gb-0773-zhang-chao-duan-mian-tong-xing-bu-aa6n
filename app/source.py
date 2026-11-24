from app.config import SAMPLE_ROOT, SOURCE_LIMIT
from app.errors import TideError
from app.modules.intake.contract import HEADERS, TRIAL_HEADERS

SAMPLES = ('dirty', 'clean', 'tide2', 'tide2_dirty')
TRIAL_SAMPLES = frozenset({'tide2', 'tide2_dirty'})


def load_sources(payload):
    if not isinstance(payload, dict):
        raise TideError('BAD_SOURCE', '请选择样例或提交潮汐资料')
    if set(payload) == {'sample'}:
        sample = payload['sample']
        if sample not in SAMPLES:
            raise TideError('NO_SAMPLE', '找不到样例簿', 404)
        names = TRIAL_HEADERS if sample in TRIAL_SAMPLES else HEADERS
        return {name: (SAMPLE_ROOT / sample / f'{name}.csv').read_bytes().decode() for name in names}
    sources = payload.get('sources')
    if set(payload) != {'sources'} or not isinstance(sources, dict) or set(sources) not in (set(HEADERS), set(TRIAL_HEADERS)):
        raise TideError('BAD_SOURCE', '请提交潮尺、站点、船期 CSV（清淤试算可另附候选表）')
    if any(not isinstance(text, str) for text in sources.values()):
        raise TideError('BAD_SOURCE', 'CSV 内容应为字符串')
    try:
        if any(len(text.encode('utf-8')) > SOURCE_LIMIT for text in sources.values()):
            raise TideError('TOO_LARGE', '单份资料超过 256 KB', 413)
    except UnicodeEncodeError as exc:
        raise TideError('BAD_SOURCE', 'CSV 内容含非法字符') from exc
    return sources
