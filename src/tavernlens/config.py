import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def user_dir() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'TavernLens'


def catalog() -> dict:
    path = Path(__file__).parent / 'data/catalog.json'
    return json.loads(path.read_text(encoding='utf-8'))


def detect_logs() -> str:
    candidates = []
    if sys.platform == 'win32':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for key in (r'SOFTWARE\WOW6432Node\Blizzard Entertainment\Hearthstone',
                        r'SOFTWARE\Blizzard Entertainment\Hearthstone'):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        candidates.append(Path(winreg.QueryValueEx(k, 'InstallLocation')[0]) / 'Logs')
                except OSError:
                    pass
    for drive in ('C:', 'D:', 'E:', 'F:'):
        for folder in ('Programs/Hearthstone', 'Program Files (x86)/Hearthstone', 'Hearthstone'):
            candidates.append(Path(drive + '/') / folder / 'Logs')
    return str(next((p for p in candidates if p.is_dir()), ''))


@dataclass
class Config:
    logs: str = ''
    mmr: str = '100'
    period: str = 'last-patch'
    mode: str = 'solo'
    scale: float = 1.0
    # X/Y offsets as proportions of the game CLIENT area, per selection type.
    offsets: dict = field(default_factory=lambda: {'hero': [0.0, 0.0], 'trinket': [0.0, 0.0]})

    @classmethod
    def load(cls, path: Path):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data,dict):
                raise ValueError('设置必须是对象')
            c = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except FileNotFoundError:
            c = cls()
        except (ValueError, TypeError) as e:
            raise ValueError('设置文件格式错误') from e
        if c.mmr not in {'100','50','25','10','1'} or c.period not in {'last-patch','past-seven','past-three','all-time'}:
            raise ValueError('统计筛选设置无效')
        if c.mode not in {'solo','duo'} or not isinstance(c.scale, (int,float)) or not .6 <= c.scale <= 2:
            raise ValueError('显示设置无效')
        if not isinstance(c.logs,str) or not isinstance(c.offsets,dict):
            raise ValueError('日志目录或位置设置无效')
        for kind in ('hero','trinket'):
            value = c.offsets.get(kind)
            if not isinstance(value,list) or len(value)!=2 or any(type(n) not in (int,float) or not -.5<=n<=.5 for n in value):
                raise ValueError('评分条位置无效')
        c.logs = c.logs or detect_logs()
        return c

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(asdict(self),ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(path)
