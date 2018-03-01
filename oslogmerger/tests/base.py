import mock
from oslotest import base


class BaseTestCase(base.BaseTestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.addCleanup(mock.patch.stopall)
