from oslogmerger import oslogmerger as om
from oslogmerger.tests import base


class PathManipulationTests(base.BaseTestCase):
    def test_get_path_and_alias(self):
        self.assertEqual(
            om.get_path_and_alias('filename', '/base/', '.log'),
            ('/base/filename.log', None, False))

        self.assertEqual(
            om.get_path_and_alias('filename:alias', '/base/', '.log'),
            ('/base/filename.log', 'alias', False))

    def test_get_path_and_alias_http(self):
        self.assertEqual(
            om.get_path_and_alias('http://server/filename.log', '', ''),
            ('http://server/filename.log', None, True))
