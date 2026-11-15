import argparse
import json
import logging
from pathlib import Path
from .config import Config, catalog, user_dir
from .engine import Engine
from .providers.firestone import Firestone


def main(argv=None):
    parser = argparse.ArgumentParser(description='TavernLens · HDT 英雄与饰品统计数据服务')
    parser.add_argument('--replay',type=Path,help='离线输出日志中的选择事件')
    parser.add_argument('--check-data',action='store_true',help='检查统计接口后退出')
    parser.add_argument('--state-dir',type=Path,default=user_dir())
    parser.add_argument('--idle-timeout',type=float,default=0,help='HDT 断开后多少秒自动退出，0 为禁用')
    parser.add_argument('--install',action='store_true',help='安装到当前用户的 HDT 插件目录')
    parser.add_argument('--quiet',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.install:
        from .installer import main as install
        return install(quiet=args.quiet)
    args.state_dir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=args.state_dir/'tavernlens.log',level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    config = Config.load(args.state_dir/'settings.json')
    if args.replay:
        engine = Engine(catalog())
        count = {'hero':0,'trinket':0}
        def consume(events):
            for event,offer in events:
                if event=='offer':
                    count[offer.kind]+=1
                    print(json.dumps({'kind':offer.kind,'cards':[o.card_id for o in offer.options]},ensure_ascii=False))
        with args.replay.open(encoding='utf-8',errors='replace') as file:
            for line in file:
                consume(engine.process(line))
        consume(engine.idle())
        print(json.dumps(count))
        return 0
    if args.check_data:
        ok=True
        for kind in ('hero','trinket'):
            table=Firestone(args.state_dir/'cache').load(kind,config.mmr,config.period,config.mode,refresh=True)
            print(json.dumps({'kind':kind,'rows':len(table.rows),'updated_at':table.updated_at,
                              'stale':table.stale,'error':table.error},ensure_ascii=False))
            ok=ok and bool(table.rows) and not table.stale
        return 0 if ok else 1
    from .service import Service
    try:
        Service(args.state_dir).run(args.idle_timeout)
    except OSError:
        logging.exception('Unable to start data service (another instance may already be running)')
        return 1
    return 0
