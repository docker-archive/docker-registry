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

'''Monkeypatch s3 boto library for unittesting.
XXX this mock is crass and break gcs.
Look into moto instead.'''

import boto.s3.bucket
import boto.s3.connection
import boto.s3.key

from . import mock_dict
from . import utils

Bucket__init__ = boto.s3.bucket.Bucket.__init__


class MultiPartUpload(boto.s3.multipart.MultiPartUpload):
    __metaclass__ = utils.monkeypatch_class

    def upload_part_from_file(self, io, num_part):
        if num_part == 1:
            self.bucket._bucket[self.bucket.name][self._tmp_key] = io.read()
        else:
            self.bucket._bucket[self.bucket.name][self._tmp_key] += io.read()

    def complete_upload(self):
        return None


class S3Connection(boto.s3.connection.S3Connection):
    __metaclass__ = utils.monkeypatch_class

    def __init__(self, *args, **kwargs):
        return None

    def get_bucket(self, name, **kwargs):
        # Create a bucket for testing
        bucket = Bucket(connection=self, name=name, key_class=Key)
        return bucket

    def make_request(self, *args, **kwargs):
        return 'request result'


class Bucket(boto.s3.bucket.Bucket):
    __metaclass__ = utils.monkeypatch_class

    _bucket = mock_dict.MockDict()
    _bucket.add_dict_methods()

    @property
    def _bucket_dict(self):
        if self.name in Bucket._bucket:
            return Bucket._bucket[self.name]._mock_dict

    def __init__(self, *args, **kwargs):
        Bucket__init__(self, *args, **kwargs)
        Bucket._bucket[self.name] = mock_dict.MockDict()
        Bucket._bucket[self.name].add_dict_methods()

    def delete(self):
        if self.name in Bucket._bucket:
            Bucket._bucket[self.name] = mock_dict.MockDict()
            Bucket._bucket[self.name].add_dict_methods()

    def list(self, **kwargs):
        return ([self.lookup(k) for k in self._bucket_dict.keys()]
                if self._bucket_dict else [])

    def lookup(self, key_name, **kwargs):
        if self._bucket_dict and key_name in self._bucket_dict:
            value = Bucket._bucket[self.name][key_name]
            k = Key(self)
            k.name = key_name
            k.size = len(value)
            return k

    def initiate_multipart_upload(self, key_name, **kwargs):
        # Pass key_name to MultiPartUpload
        mp = MultiPartUpload(self)
        mp._tmp_key = key_name
        return mp


class Key(boto.s3.key.Key):
    __metaclass__ = utils.monkeypatch_class

    def exists(self):
        bucket_dict = self.bucket._bucket_dict
        return self.name in bucket_dict if bucket_dict else False

    def delete(self):
        del self.bucket._bucket_dict[self.name]

    def set_contents_from_string(self, value, **kwargs):
        self.size = len(value)
        self.bucket._bucket_dict[self.name] = value

    def get_contents_as_string(self, *args, **kwargs):
        return self.bucket._bucket_dict[self.name]

    def get_contents_to_file(self, fp, **kwargs):
        min_cur, max_cur = (kwargs['headers']['Range'].replace('bytes=', '')
                            .split('-'))
        value = self.bucket._bucket_dict[self.name]
        fp.write(value[int(min_cur):int(max_cur) + 1])
        fp.flush()

    def read(self, buffer_size):
        # fetch read status
        lp = getattr(self, '_last_position', 0)
        self._last_position = lp + buffer_size
        return self.bucket._bucket_dict[self.name][lp:lp + buffer_size]
