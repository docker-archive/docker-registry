# -*- coding: utf-8 -*-

# from nose import tools

# from docker_registry.core import exceptions
# import docker_registry.testing as testing

import os
import unittest

import mock

from docker_registry.lib import config


fakeenv = {}


def mockget(key, opt=None):
    if key in fakeenv:
        print('%s key is %s' % (key, fakeenv[key]))
        return fakeenv[key]
    return opt


@mock.patch('os.environ.get', mockget)
class TestConfig(unittest.TestCase):

    def setUp(self):
        p = os.path.join(
            os.path.dirname(__file__), 'fixtures', 'test_config.yaml')

        self.c = config.Config(open(p, 'rb').read())

    def test__init__parse_error(self):
        self.assertRaises(config.exceptions.ConfigError, config.Config, '\1')

    def test__init__no_arg(self):
        self.c = config.Config()
        assert self.c['whatevertheflush'] is None
        assert self.c.whatevertheflush is None

    @mock.patch('__builtin__.repr')
    def test__repr(self, r):
        self.c.__repr__()
        r.assert_called_once_with(self.c._config)

    def test__methods__(self):
        self.assertEqual(self.c.__methods__, [])

    def test__members__(self):
        self.assertEqual(type(self.c.__members__), list)
        self.assertEqual(self.c.__members__, self.c.keys())
        self.assertEqual(self.c.__members__, self.c.__dir__())

    def test_accessors(self):
        assert self.c.booltrue == self.c['booltrue']
        assert self.c.dict.one == self.c.dict['one']
        assert self.c.dict.one == self.c['dict']['one']

    def test_key_existence(self):
        assert 'boolfalse' in self.c
        assert 'whatevertheflush' not in self.c

    def test_non_existent_access(self):
        assert self.c['whatevertheflush'] is None
        assert self.c.whatevertheflush is None

    def test_simple_types(self):
        conf = self.c
        assert conf.booltrue is True
        assert not conf.booltrue == 'True'
        assert conf.boolfalse is False
        assert not conf.booltrue == 'False'
        assert conf.uint == 10
        assert not conf.uint == '10'
        assert conf.int == -10
        assert not conf.int == '-10'
        assert conf.float == 0.01
        assert not conf.float == '0.01'
        assert conf.emptystring == ''
        assert conf.emptystring is not None
        assert conf.isnone is None
        assert conf.nonemptystring == 'nonemptystring'
        assert conf.anothernonemptystring == 'nonemptystring'
        assert conf.yetanothernonemptystring == 'nonemptystring'
        assert conf.array[2] == 'three'
        assert len(conf.array) == 3
        assert conf.dict.two == 'valuetwo'
        assert isinstance(conf.dict, config.Config)

    def test_env_defaults(self):
        global fakeenv
        fakeenv = {}

        conf = self.c.ENV
        assert conf.booltrue is True
        assert conf.boolfalse is False
        assert conf.uint == 10
        assert conf.int == -10
        assert conf.float == 0.01
        assert conf.emptystring == ''
        assert conf.emptystring is not None
        assert conf.isnone is None
        assert conf.nonemptystring == 'nonemptystring'
        assert conf.anothernonemptystring == 'nonemptystring'
        assert conf.yetanothernonemptystring == 'nonemptystring'
        assert conf.bugger == 'bug:me:endlessly'
        assert conf.array[2] == 'three'
        assert len(conf.array) == 3
        assert conf.dict is None

    def test_env_overrides(self):
        global fakeenv
        fakeenv['BOOLTRUE'] = 'False'
        fakeenv['BOOLFALSE'] = 'True'
        fakeenv['UINT'] = '0'
        fakeenv['INT'] = '0'
        fakeenv['FLOAT'] = '0'
        fakeenv['EMPTYSTRING'] = 'NOTREALLY'
        fakeenv['ISNONE'] = 'False'
        fakeenv['NONEMPTYSTRING'] = '""'
        fakeenv['BUGGER'] = '"whatever:the:flush:"'
        fakeenv['ARRAY'] = '[one, again]'
        fakeenv['DICT'] = '{"one": "oneagain", "two": "twoagain"}'

        conf = self.c.ENV
        assert conf.booltrue is False
        assert conf.boolfalse is True
        assert conf.uint == 0
        assert conf.int == 0
        assert conf.float == 0
        assert conf.emptystring == 'NOTREALLY'
        assert conf.isnone is False
        assert conf.isnone is not None
        assert conf.nonemptystring == ''
        assert conf.anothernonemptystring == 'nonemptystring'
        assert conf.yetanothernonemptystring == 'nonemptystring'
        assert conf.bugger == 'whatever:the:flush:'
        assert conf.array[1] == 'again'
        assert len(conf.array) == 2

        fakeenv['ISNONE'] = ''
        assert conf.isnone is None

        assert isinstance(conf.dict, config.Config)
        assert conf.dict.one == 'oneagain'

    def test_write(self):
        conf = self.c
        assert conf.something == 'else'
        conf.something = 'or'
        assert conf.something == 'or'
        conf.something = None
        assert conf.something is None

    def test_unicode(self):
        assert self.c.uni == u'ß∞'


class TestLoad(unittest.TestCase):

    def setUp(self):
        self._config = config._config

    def tearDown(self):
        config._config = self._config

    @mock.patch.object(config.os.environ, 'get')
    def test_config_path_exception(self, get):
        config._config = None
        self.assertRaises(config.exceptions.FileNotFoundError, config.load)
