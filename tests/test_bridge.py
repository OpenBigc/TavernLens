import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tavernlens.bridge import Bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge=Bridge(port=0)
        self.url=f'http://127.0.0.1:{self.bridge.server.server_port}'

    def tearDown(self):
        self.bridge.close()

    def test_snapshots_are_read_only_and_never_expose_log_files(self):
        self.bridge.publish({'version':1,'active':True,'kind':'hero','options':[]})
        with urllib.request.urlopen(self.url+'/state') as response:
            self.assertEqual(json.load(response)['kind'],'hero')
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))
        for suffix in ['/settings','/logs','/../Power.log']:
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+suffix)
            self.assertEqual(error.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(self.url+'/state',method='POST',data=b'{}'))
        self.assertEqual(error.exception.code,501)

    def test_hostnames_cannot_rebind_to_loopback_service(self):
        request=urllib.request.Request(self.url+'/state',headers={'Host':'example.com'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
        self.assertEqual(error.exception.code,403)


if __name__=='__main__':unittest.main()
