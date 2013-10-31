
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
