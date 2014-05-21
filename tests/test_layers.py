# -*- coding: utf-8 -*-

import backports.lzma as lzma
import os
import random
import string
import tarfile

import base
from docker_registry.lib import layers
from docker_registry import storage

from docker_registry.core import compat
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
        path_parts = layer_path.split(os.sep)
        layer_parent = os.path.join(*path_parts[:-1])
        os.makedirs(layer_parent)

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
