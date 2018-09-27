# Copyright 2018 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

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
