import mock

from docker_registry.lib import checksums
from tests.base import TestCase


class TestShaMethods(TestCase):

    def test_sha256_file(self):
        self.assertEqual(
            checksums.sha256_file(None, None),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        self.assertEqual(
            checksums.sha256_file(None, 'test'),
            '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08')

    def test_compute_simple(self):
        out = checksums.compute_simple(None, '')
        self.assertTrue(out.startswith('sha256:'))
        nl = '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'
        self.assertTrue(out.endswith(nl))

        out = checksums.compute_simple(None, 'test')
        h = 'f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2'
        self.assertTrue(out.endswith(h))


class TestTarSum(TestCase):

    def setUp(self):
        self.tar_sum = checksums.TarSum(None)

    def test_append(self):
        self.tar_sum.header_fields = tuple()
        member = mock.MagicMock(size=1)
        tarobj = mock.MagicMock(
            extractfile=mock.MagicMock(side_effect=KeyError))
        self.tar_sum.append(member, tarobj)
        self.assertEqual(len(self.tar_sum.hashes), 1)
        self.assertEqual(
            self.tar_sum.hashes[0],
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
