# Third-party notices

## bgtracker

`src/tavernlens/detection.py` adapts `normalize`, `ChoiceReader`, `OfferDetector`
and the associated regular expressions from:

- https://github.com/BattlegroundsHelp/bgtracker
- Commit: `2dd836f165657de06620c1ae7feed3ffdf53a5fb`
- Copyright (c) 2026 the bgtracker contributors
- License: MIT, included in LICENSE

`tests/fixtures/offers.log`, `hero_ids.json`, and `trinket_ids.json` are public
regression fixtures from the same repository. The HDT adapter starts with the
upstream hero/trinket horizontal slot measurements; below-card positions,
client-area mapping and configuration are implemented here.

## Hearthstone Deck Tracker

The optional host integration implements the documented IPlugin API and uses
API.Core.OverlayCanvas. HDT is Copyright HearthSim, All Rights Reserved.
No HDT executable, implementation source, assets or assemblies are distributed.
Builds reference the user's separately installed copy. The test host is an
independent minimal implementation of the documented public interface only.

## HearthstoneJSON / Blizzard

The compact catalog is derived from HearthstoneJSON's zhCN card database:
https://api.hearthstonejson.com/v1/latest/zhCN/cards.json

Hearthstone and card names are property of Blizzard Entertainment, Inc.
No card artwork is distributed. This project is not affiliated with Blizzard.

## Firestone statistics

The app reads endpoints identified in Zero-to-Heroes/firestone's published
client source. No Firestone source code or collected statistics are bundled.
Public reachability is not a grant of redistribution rights or an API service
commitment. The MIT license here applies to our code, not to third-party data.

## Packaged runtime

Windows binaries bundle CPython and native runtime dependencies. Their notices
are included in the release's `runtime-licenses` directory. These components
retain their own licenses; the project's MIT license does not replace them.
