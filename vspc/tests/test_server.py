# Copyright (c) 2017 VMware Inc.
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
import mock
import testtools

from vspc import server


class VspcServerTest(testtools.TestCase):

    def test_handle_vm_vc_uuid(self):
        mock_socket = mock.Mock()
        srv = server.VspcServer()
        data = b'11 22 33 44 55'
        srv.handle_vm_vc_uuid(mock_socket, data)
        actual_uuid = srv.sock_to_uuid[mock_socket]
        self.assertEqual('1122334455', actual_uuid)
