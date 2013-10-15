"""
Elliptics is a fault tolerant distributed key/value storage.
See: http://reverbrain.com/elliptics and
https://github.com/reverbrain/elliptics
"""

import itertools

import cache

from . import Storage

import elliptics

NAMESPACE = "DOCKER"


class EllipticsStorage(Storage):

    def __init__(self, config):
        cfg = elliptics.Config()
        log = elliptics.Logger("/dev/stderr", config.get('verbosity', 0))

        cfg.config.wait_timeout = config.get("wait-timeout", 60)
        cfg.config.io_thread_num = config.get("io-thread-num", 1)
        cfg.config.net_thread_num = config.get("net-thread-num", 1)
        cfg.config.groups = config.get('groups', [])

        self._elliptics_node = elliptics.Node(log, cfg)
        for host, port in config.get('nodes').iteritems():
            self._elliptics_node.add_remote(host, port)

        self._session = elliptics.Session(self._elliptics_node)
        self._session.groups = config.get('groups', [])
        if len(self._session.groups) == 0:
            raise ValueError("Specify groups")
        self._session.set_namespace(NAMESPACE)

    def s_find(self, tags):
        r = self._session.find_all_indexes(list(tags))
        r.wait()
        result = r.get()
        return [i.indexes[0].data for i in itertools.chain(result)]

    def s_remove(self, key):
        self._session.remove(key)
        self._session.set_indexes(key, [], [])

    def s_read(self, path):
        res = self._session.read_data(path, 0, 0).get()[0]
        return res.data

    def s_write(self, key, value, tags):
        self._session.write_data(key, str(value)).wait()
        r = self._session.set_indexes(key, list(tags), [key] * len(tags))
        r.wait()
        return r.successful()

    @cache.get
    def get_content(self, path):
        try:
            return self.s_read(path)
        except Exception as err:
            raise IOError(err)

    @cache.put
    def put_content(self, path, content):
        tag, _, _ = path.rpartition('/')
        if len(content) == 0:
            content = "EMPTY"
        self.s_write(path, content, ('docker', tag))
        spl_path = path.rsplit('/')[:-1]
        while spl_path:
            _path = '/'.join(spl_path)
            _tag = '/'.join(spl_path[:-1])
            spl_path.pop()
            self.s_write(_path, "DIRECTORY", ('docker', _tag))
        return path

    def stream_write(self, path, fp):
        chunks = []
        while True:
            try:
                buf = fp.read(self.buffer_size)
                if not buf:
                    break
                chunks += buf
            except IOError:
                break
        self.put_content(path, ''.join(chunks))

    def stream_read(self, path):
        yield self.get_content(path)

    def list_directory(self, path=None):
        if path is None:
            path = ""

        items = self.s_find(('docker', path))
        if not items:
            raise OSError('No such directory: \'{0}\''.format(path))

        for item in items:
            yield item

    def exists(self, path):
        tag, _, _ = path.rpartition('/')
        res = self.s_find(('docker', tag))
        return path in res

    @cache.remove
    def remove(self, path):
        self.s_remove(path)

    def get_size(self, path):
        return len(self.get_content(path))
