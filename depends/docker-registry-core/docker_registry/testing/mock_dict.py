# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Extend Mock class with dictionary behavior.
   Call it as:
       mocked_dict = MockDict()
       mocked_dict.add_dict_methods()'''

import mock

MagicMock__init__ = mock.MagicMock.__init__


class MockDict(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        MagicMock__init__(self, *args, **kwargs)
        self._mock_dict = {}

    @property
    def get_dict(self):
        return self._mock_dict

    def add_dict_methods(self):
        def setitem(key, value):
            self._mock_dict[key] = value

        def delitem(key):
            del self._mock_dict[key]

        self.__getitem__.side_effect = lambda key: self._mock_dict[key]
        self.__setitem__.side_effect = setitem
        self.__delitem__.side_effect = delitem
        self.__contains__.side_effect = lambda key: key in self._mock_dict
