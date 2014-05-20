# -*- coding: utf-8 -*-

import unittest

import docker_registry.run as run

import mock


class TestRunGunicorn(unittest.TestCase):
    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_exec_gunicorn(self, mock_execl, mock_parse_args):
        run.run_gunicorn()

        self.assertEqual(mock_execl.call_count, 1)
        # ensure that the executable's path ends with 'gunicorn', so we have
        # some confidence that it called the correct executable
        self.assertTrue(mock_execl.call_args[0][0].endswith('gunicorn'))

    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_parses_args(self, mock_execl, mock_parse_args):
        run.run_gunicorn()

        # ensure that argument parsing is happening
        mock_parse_args.assert_called_once_with()

    @mock.patch('sys.exit')
    @mock.patch('distutils.spawn.find_executable', autospec=True)
    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_gunicorn_not_found(self, mock_execl, mock_parse_args,
                                mock_find_exec, mock_exit):
        mock_find_exec.return_value = None

        run.run_gunicorn()

        # ensure that sys.exit was called
        mock_exit.assert_called_once_with(1)
