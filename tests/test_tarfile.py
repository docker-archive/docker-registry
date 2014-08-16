# -*- coding: utf-8 -*-

import imp
import os

import base
from nose import tools

from docker_registry.lib import checksums
from docker_registry.lib import xtarfile


# setting like this in test, due to flake8 H302
tarfile = xtarfile.tarfile

# To test whether the UnicodeDecodeError still exists
# (it's still present in python 3.4.0)
# ((loading this way, since we've monkey patched currently loaded tarfile))
tarfile_vanilla = imp.load_module('test_failing', *imp.find_module('tarfile'))


class TestTarfile(base.TestCase):
    @tools.raises(UnicodeDecodeError)
    def test_vanilla_tarfile(self):
        layer_fh = open(os.path.join(base.data_dir, "xattr/layer.tar"))
        tar = tarfile_vanilla.open(mode='r|*', fileobj=layer_fh)
        assert tar

    def test_headers(self):
        expected = {
            "46af0962ab5afeb5ce6740d4d91652e69206fc991fd5328c1a94d364ad00e457/layer.tar": {  # noqa
                "dev": {
                    "headers": {"size": 0, "mode": 0o40755, "type": "5"},
                    "pax": {},
                },
                "dev/core": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "dev/stderr": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "dev/stdout": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "dev/fd": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "dev/ptmx": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "dev/stdin": {
                    "headers": {"size": 0, "mode": 0o120777, "type": "2"},
                    "pax": {},
                },
                "etc": {
                    "headers": {"size": 0, "mode": 0o40755, "type": "5"},
                    "pax": {},
                },
                "etc/sudoers": {
                    "headers": {"size": 3348, "mode": 0o100440, "type": "0"},
                    "pax": {},
                },
            },
            "511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158/layer.tar": {  # noqa
                ".": {
                    "headers": {"size": 0, "mode": 0o40755, "type": "5"},
                    "pax": {},
                },
            },
            "xattr/layer.tar": {
                "file": {
                    "headers": {"size": 0, "mode": 0o100644, "type": "0"},
                    "pax": {u"SCHILY.xattr.security.capability": "\x01\x00\x00\x02\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"},  # noqa
                },
            },
        }
        for file in expected.keys():
            layer_fh = open(os.path.join(base.data_dir, file))
            tar = tarfile.open(mode='r|*', fileobj=layer_fh)
            member_count = 0
            for member in tar:
                member_count += 1
                # check that we know the file names
                msg = "in %s, did not find file %s" % (file, member.path)
                l = len(filter(lambda x: member.path in x,
                        expected[file].keys()))
                assert (l > 0), msg
                e = expected[file][member.path]
                for attr in e["headers"].keys():
                    msg = "in %s:%s, expected %s of %s, but got %s" % (
                        file, member.path, attr, e["headers"][attr],
                        getattr(member, attr))
                    assert e["headers"][attr] == getattr(member, attr), msg
                for attr in e["pax"].keys():
                    msg = b"in %s:%s, expected %s of %s, but got %s".format(
                        file, member.path, attr, e["pax"][attr],
                        member.pax_headers[attr])
                    assert e["pax"][attr] == member.pax_headers[attr], msg

            assert member_count == len(expected[file])
            layer_fh.close()

    def test_tarsum(self):
        expected = {
            "46af0962ab5afeb5ce6740d4d91652e69206fc991fd5328c1a94d364ad00e457": "tarsum+sha256:e58fcf7418d4390dec8e8fb69d88c06ec07039d651fedd3aa72af9972e7d046b",  # noqa
            "511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158": "tarsum+sha256:ac672ee85da9ab7f9667ae3c32841d3e42f33cc52c273c23341dabba1c8b0c8b",  # noqa
            "xattr": "tarsum+sha256:e86f81a4d552f13039b1396ed03ca968ea9717581f9577ef1876ea6ff9b38c98",  # noqa
        }
        for layer in expected.keys():
            layer_fh = open(os.path.join(base.data_dir, layer, "layer.tar"))
            json_fh = open(os.path.join(base.data_dir, layer, "json"))

            tarsum = checksums.TarSum(json_fh.read())
            tar = tarfile.open(mode='r|*', fileobj=layer_fh)
            for member in tar:
                tarsum.append(member, tar)
            sum = tarsum.compute()
            msg = "layer %s, expected [%s] but got [%s]" % (
                layer, expected[layer], sum)
            assert expected[layer] == sum, msg

            layer_fh.close()
            json_fh.close()
