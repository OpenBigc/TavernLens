import json
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tavernlens.service import Service
from tavernlens.config import Config
from tavernlens.models import Offer, Option, Table


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=Path(self.temp.name)
        self.service=Service.__new__(Service)
        s=self.service
        s.path=self.folder/'settings.json';s.config=Config(logs='test')
        s.config.save(s.path)
        info=s.path.stat();s.last_mtime=(info.st_mtime_ns,info.st_size)
        s.refreshed=time.monotonic();s.generation=2;s.log_generation=2
        s.tables={};s.queue=queue.Queue();s.log_status='等待日志'
        s.active=Offer('hero',(Option('H1','英雄一',1),Option('H2','英雄二',2)))
        s.until=time.monotonic()+60;s.bridge=Mock()

    def tearDown(self):self.temp.cleanup()

    def test_old_reader_and_old_filter_results_cannot_overwrite_current_selection(self):
        s=self.service
        s.queue.put(('log',(1,('hide',None))))
        s.queue.put(('table',(1,Table('hero'))))
        s.tick()
        self.assertIsNotNone(s.active)
        self.assertEqual(s.tables,{})
        state=s.bridge.publish.call_args.args[0]
        self.assertTrue(state['active'])
        self.assertEqual([x['slot'] for x in state['options']],[1,2])

    def test_invalid_settings_are_not_retried_and_logged_every_tick(self):
        s=self.service
        stamp=s.path.stat().st_mtime_ns
        s.path.write_text('{bad json',encoding='utf-8')
        # Some Windows filesystems expose equal timestamps for fast writes.
        os.utime(s.path,ns=(stamp,stamp))
        with patch('tavernlens.service.logging.exception') as log:
            s.config_changed();s.config_changed()
        self.assertEqual(log.call_count,1)
        self.assertEqual(s.config.mmr,'100')

    def test_wrong_config_types_are_rejected(self):
        for data in ([],{'logs':123},{'offsets':[]},{'scale':float('nan')}):
            self.service.path.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError):Config.load(self.service.path)


if __name__=='__main__':unittest.main()
