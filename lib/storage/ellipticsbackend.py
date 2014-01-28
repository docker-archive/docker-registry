"""
Elliptics is a fault tolerant distributed key/value storage.
See http://reverbrain.com/elliptics and
https://github.com/reverbrain/elliptics for additional info.

Docs: http://doc.reverbrain.com/
Deployment guide: http://doc.reverbrain.com/elliptics:server-tutorial
Packages: http://repo.reverbrain.com/
"""

import itertools
import logging

import cache_lru

from . import Storage

import elliptics


DEFAULT_NAMESPACE = "DOCKER"
logger = logging.getLogger(__name__)


class EllipticsStorage(Storage):

    def __init__(self, config):
        cfg = elliptics.Config()
        # The parameter which sets the time to wait for the operation complete
        cfg.config.wait_timeout = config.get("elliptics_wait_timeout", 60)
        # The parameter which sets the timeout for pinging node
        cfg.config.check_timeout = config.get("elliptics_check_timeout", 60)
        # Number of IO threads in processing pool
        cfg.config.io_thread_num = config.get("elliptics_io_thread_num", 2)
        # Number of threads in network processing pool
        cfg.config.net_thread_num = config.get("elliptics_net_thread_num", 2)
        # Number of IO threads in processing pool dedicated to nonblocking ops
        nblock_iothreads = config.get("elliptics_nonblocking_io_thread_num", 2)
        cfg.config.nonblocking_io_thread_num = nblock_iothreads
        self.groups = config.get('elliptics_groups', [])
        if len(self.groups) == 0:
            raise ValueError("Specify groups")

        # loglevel of elliptics logger
        elliptics_log_level = config.get('elliptics_verbosity', 0)

        # path to logfile
        elliptics_log_file = config.get('elliptics_logfile', '/dev/stderr')
        log = elliptics.Logger(elliptics_log_file, elliptics_log_level)
        self._elliptics_node = elliptics.Node(log, cfg)

        self.namespace = config.get('elliptics_namespace', DEFAULT_NAMESPACE)
        logger.info("Using namespace %s", self.namespace)

        at_least_one = False
        for host, port in config.get('elliptics_nodes').iteritems():
            try:
                self._elliptics_node.add_remote(host, port)
                at_least_one = True
            except Exception as err:
                logger.error("Failed to add remote %s:%d %s", host, port, err)

        if not at_least_one:
            raise Exception("Unable to connect to Elliptics")

    @property
    def _session(self):
        session = elliptics.Session(self._elliptics_node)
        session.groups = self.groups
        session.set_namespace(self.namespace)
        session.exceptions_policy = elliptics.exceptions_policy.no_exceptions
        return session

    def s_find(self, tags):
        r = self._session.find_all_indexes(list(tags))
        r.wait()
        result = r.get()
        return [str(i.indexes[0].data) for i in itertools.chain(result)]

    def s_remove(self, key):
        self._session.remove(key).wait()
        self._session.set_indexes(key, [], []).wait()

    def s_read(self, path):
        r = self._session.read_data(path, offset=0, size=0)
        r.wait()
        err = r.error()
        if err.code != 0:
            raise IOError("Reading failed {0}".format(err))

        res = r.get()[0]
        return str(res.data)

    def s_write(self, key, value, tags):
        # Write data with given key
        r = self._session.write_data(key, str(value))
        r.wait()
        err = r.error()
        if err.code != 0:
            raise IOError("Writing failed {0}".format(err))

        # Set indexes
        r = self._session.set_indexes(key, list(tags), [key] * len(tags))
        r.wait()
        if err.code != 0:
            raise IOError("Setting indexes failed {0}".format(err))

    @cache_lru.get
    def get_content(self, path):
        try:
            return self.s_read(path)
        except Exception as err:
            raise IOError(err)

    @cache_lru.put
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

    def stream_read(self, path, bytes_range=None):
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

    @cache_lru.remove
    def remove(self, path):
        self.s_remove(path)

    def get_size(self, path):
        return len(self.get_content(path))
