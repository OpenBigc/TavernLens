from dataclasses import dataclass, field
from typing import Literal

Kind = Literal['hero', 'trinket']


@dataclass(frozen=True)
class Option:
    card_id: str
    name: str
    slot: int


@dataclass(frozen=True)
class Offer:
    kind: Kind
    options: tuple[Option, ...]


@dataclass(frozen=True)
class Stat:
    average: float | None
    samples: int
    pick_rate: float | None = None
    pick_scope: str = 'selected'


@dataclass(frozen=True)
class Table:
    kind: Kind
    rows: dict[str, Stat] = field(default_factory=dict)
    updated_at: str | None = None
    fetched_at: float | None = None
    stale: bool = False
    error: str | None = None


@dataclass(frozen=True)
class Badge:
    slot: int
    average: str
    details: str
    color: str


def badges(offer: Offer, table: Table | None) -> tuple[Badge, ...]:
    from .detection import normalize
    output = []
    for option in sorted(offer.options, key=lambda x: x.slot):
        row = table.rows.get(normalize(option.card_id, table.rows)) if table else None
        if not row or row.average is None:
            output.append(Badge(option.slot, '—', '暂无数据' if table else '加载中', '#a2a8b3'))
            continue
        scope = '总体选择' if row.pick_scope == 'all' else '选择'
        pick = f'{scope}{row.pick_rate:.0f}% · ' if row.pick_rate is not None else ''
        small = f'{pick}{row.samples:,}场'
        if row.samples < 30:
            small += ' · 样本少'
        if table.stale:
            small += ' · 旧缓存'
        color = '#86d8ae' if row.average < 4.2 else '#e0c587' if row.average < 4.7 else '#e39c98'
        output.append(Badge(option.slot, f'均次 {row.average:.2f}', small, color))
    return tuple(output)
