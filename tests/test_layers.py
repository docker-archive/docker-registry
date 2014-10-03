# -*- coding: utf-8 -*-

import os
import random
import string
import tarfile

import backports.lzma as lzma
import base
import mock

from docker_registry.core import compat
from docker_registry.lib import layers
from docker_registry import storage

json = compat.json
StringIO = compat.StringIO


# from mock import patch
# from mockredis import mock_strict_redis_client


def comp(n, f, *args, **kwargs):
    return (f(*args, **kwargs) for i in xrange(n))


def rndstr(length=5):
    palette = string.ascii_uppercase + string.digits
    return ''.join(comp(length, random.choice, palette))


def _get_tarfile(filenames):
    tfobj = StringIO()
    tar = tarfile.TarFile(fileobj=tfobj, mode='w')
    data = rndstr(512)
    for filename in filenames:
        tarinfo = tarfile.TarInfo(filename)
        tarinfo.size = len(data)
        io = StringIO()
        io.write(data)
        io.seek(0)
        tar.addfile(tarinfo, io)
    tfobj.seek(0)
    return tfobj


def _get_xzfile(filenames):
    tar_data = _get_tarfile(filenames)
    lzma_fobj = StringIO()
    xz_file = lzma.open(lzma_fobj, 'w')
    xz_file.write(tar_data.read())
    xz_file.close()
    lzma_fobj.seek(0)
    return lzma_fobj


class TestHelpers(base.TestCase):

    @mock.patch.object(layers.cache, 'redis_conn')
    @mock.patch.object(layers.diff_queue, 'push')
    @mock.patch.object(layers.logger, 'warning')
    def test_enqueue_diff(self, logger, diff_queue, redis):
        redis.return_value = False
        self.assertEqual(logger.call_count, 0)
        diff_queue.return_value = mock.MagicMock()
        redis.return_value = True
        image_id = 'abcd'
        layers.enqueue_diff(image_id)
        diff_queue.assert_called_once_with(image_id)
        self.assertEqual(logger.call_count, 0)
        diff_queue.side_effect = layers.cache.redis.exceptions.ConnectionError
        layers.enqueue_diff(image_id)
        self.assertEqual(logger.call_count, 1)


class TestArchive(base.TestCase):

    def setUp(self):
        self.archive = layers.Archive(_get_tarfile(list(comp(5, rndstr))))

    def test_properties(self):
        self.assertEqual(self.archive.seekable(), True)
        self.assertEqual(self.archive.readable(), True)
        self.assertEqual(self.archive._check_can_seek(), True)


class TestTarFilesInfo(base.TestCase):

    def setUp(self):
        self.tar_files_info = layers.TarFilesInfo()

    def test__init__(self):
        self.assertEqual(type(self.tar_files_info.infos), list)

    @mock.patch('docker_registry.lib.layers.serialize_tar_info')
    def test_append(self, serialize_tar_info):
        tar_info = ('test', True)
        serialize_tar_info.return_value = tar_info
        self.assertEqual(len(self.tar_files_info.infos), 0)
        self.assertEqual(self.tar_files_info.append('test'), None)
        self.assertNotEqual(len(self.tar_files_info.infos), 0)
        self.assertTrue(tar_info in self.tar_files_info.infos)

    def test_json(self):
        self.assertEqual(type(self.tar_files_info.json()), str)
        self.assertEqual(self.tar_files_info.json(), '[]')


class TestLayers(base.TestCase):

    def setUp(self):
        self.store = storage.load(kind='file')
        self.filenames = list(comp(5, rndstr))

    def test_tar_archive(self):
        tfobj = _get_tarfile(self.filenames)

        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            assert tarinfo.name in self.filenames

    def test_xz_archive(self):
        tfobj = _get_xzfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            assert tarinfo.name in self.filenames

    def test_info_serialization(self):
        tfobj = _get_tarfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            sinfo = layers.serialize_tar_info(tarinfo)
            assert sinfo[0] in self.filenames
            assert sinfo[1:] == ('f', False, 512, 0, 420, 0, 0)

        tar_info = mock.MagicMock()
        expectations = [(".", "/"), ("./", "/"), ("./ab", "/ab")]
        for name_in, name_out in expectations:
            tar_info.name = name_in
            out = layers.serialize_tar_info(tar_info)
            self.assertEqual(out[0], name_out)
            self.assertEqual(out[2], False)
        tar_info.name = "./.wh..wh."
        self.assertEqual(layers.serialize_tar_info(tar_info), None)
        expectations = [("./.wh.", "/"), ("/.wh.", "/")]
        for name_in, name_out in expectations:
            tar_info.name = name_in
            out = layers.serialize_tar_info(tar_info)
            self.assertEqual(out[0], name_out)
            self.assertEqual(out[2], True)

    def test_tar_serialization(self):
        tfobj = _get_tarfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        infos = layers.read_tarfile(tar)
        for tarinfo in infos:
            assert tarinfo[0] in self.filenames
            assert tarinfo[1:] == ('f', False, 512, 0, 420, 0, 0)

    def test_layer_cache(self):
        layer_id = rndstr(16)
        layers.set_image_files_cache(layer_id, "{}")
        fetched_json = layers.get_image_files_cache(layer_id)
        assert fetched_json == "{}"

    def test_tar_from_fobj(self):
        tfobj = _get_tarfile(self.filenames)
        files = layers.get_image_files_from_fobj(tfobj)
        for file in files:
            assert file[0] in self.filenames
            assert file[1:] == ('f', False, 512, 0, 420, 0, 0)

    def test_get_image_files_json_cached(self):
        layer_id = rndstr(16)
        layers.set_image_files_cache(layer_id, "{}")
        files_json = layers.get_image_files_json(layer_id)
        assert files_json == "{}"

    def test_get_image_files_json(self):
        layer_id = rndstr(16)
        tfobj = _get_tarfile(self.filenames)

        layer_path = self.store.image_layer_path(layer_id)
        layer_path = os.path.join(self.store._root_path, layer_path)
        os.makedirs(os.path.dirname(layer_path))

        with open(layer_path, 'w') as fobj:
            fobj.write(tfobj.read())

        files_json = layers.get_image_files_json(layer_id)
        file_infos = json.loads(files_json)
        for info in file_infos:
            assert info[0] in self.filenames
            assert info[1:] == [u"f", False, 512, 0, 420, 0, 0]

    def test_get_file_info_map(self):
        files = (
            ("test", "f", False, 512, 0, 420, 0, 0),
        )
        map = layers.get_file_info_map(files)
        assert "test" in map
        assert map['test'] == ("f", False, 512, 0, 420, 0, 0)

    def test_image_diff_cache(self):
        layer_id = rndstr(16)
        layers.set_image_diff_cache(layer_id, layer_id)
        diff_json = layers.get_image_diff_cache(layer_id)
        assert layer_id == diff_json

    def test_image_diff_json(self):
        layer_1 = (
            ("deleted", "f", False, 512, 0, 420, 0, 0),
            ("changed", "f", False, 512, 0, 420, 0, 0),
        )

        layer_2 = (
            ("deleted", "f", True, 512, 0, 420, 0, 0),
            ("changed", "f", False, 512, 0, 420, 0, 0),
            ("created", "f", False, 512, 0, 420, 0, 0),
        )
        layer_1_id = rndstr(16)
        layer_2_id = rndstr(16)

        ancestry = json.dumps([layer_2_id, layer_1_id])
        ancestry_path = self.store.image_ancestry_path(layer_2_id)
        self.store.put_content(ancestry_path, ancestry)

        layer_1_files_path = self.store.image_files_path(layer_1_id)
        self.store.put_content(layer_1_files_path, json.dumps(layer_1))

        layer_2_files_path = self.store.image_files_path(layer_2_id)
        self.store.put_content(layer_2_files_path, json.dumps(layer_2))

        diff_json = layers.get_image_diff_json(layer_2_id)
        diff = json.loads(diff_json)

        for type in ("deleted", "changed", "created"):
            assert type in diff
            assert type in diff[type]

    @mock.patch('docker_registry.lib.layers.get_image_diff_cache')
    def test_get_image_diff_json(self, get_image_diff_cache):
        diff_json = 'test'
        get_image_diff_cache.return_value = diff_json
        self.assertEqual(layers.get_image_diff_json(1), diff_json)
