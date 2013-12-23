"""
Elliptics is a fault tolerant distributed key/value storage.
See http://reverbrain.com/elliptics and
https://github.com/reverbrain/elliptics for additional info.

Docs: http://doc.reverbrain.com/
Deployment guide: http://doc.reverbrain.com/elliptics:server-tutorial
Packages: http://repo.reverbrain.com/
"""

import itertools

import cache

from . import Storage

import elliptics

NAMESPACE = "DOCKER"


class EllipticsStorage(Storage):

    def __init__(self, config):
        cfg = elliptics.Config()
        # The parameter which sets the time to wait for the operation complete
        cfg.config.wait_timeout = config.get("wait-timeout", 60)
        # The parameter which sets the timeout for pinging node
        cfg.config.check_timeout = config.get("check_timeout", 60)
        # Number of IO threads in processing pool
        cfg.config.io_thread_num = config.get("io-thread-num", 2)
        # Number of threads in network processing pool
        cfg.config.net_thread_num = config.get("net-thread-num", 2)
        # Number of IO threads in processing pool dedicated to nonblocking ops
        nonblock_io_threads = config.get("nonblocking_io_thread_num", 2)
        cfg.config.nonblocking_io_thread_num = nonblock_io_threads
        groups = config.get('groups', [])
        if len(groups) == 0:
            raise ValueError("Specify groups")

        # loglevel of elliptics logger
        elliptics_log_level = config.get('verbosity', 0)

        # path to logfile
        elliptics_log_file = config.get('logfile', '/dev/stderr')
        log = elliptics.Logger(elliptics_log_file, elliptics_log_level)
        self._elliptics_node = elliptics.Node(log, cfg)

        for host, port in config.get('nodes').iteritems():
            self._elliptics_node.add_remote(host, port)

        self._session = elliptics.Session(self._elliptics_node)
        self._session.groups = groups
        self._session.set_namespace(NAMESPACE)

    def s_find(self, tags):
        r = self._session.find_all_indexes(list(tags))
        r.wait()
        result = r.get()
        return [str(i.indexes[0].data) for i in itertools.chain(result)]

    def s_remove(self, key):
        self._session.remove(key)
        self._session.set_indexes(key, [], [])

    def s_read(self, path):
        res = self._session.read_data(path, offset=0, size=0).get()[0]
        return str(res.data)

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
