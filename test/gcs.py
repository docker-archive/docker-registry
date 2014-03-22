
import test_storage

from docker_registry import storage


class TestGSStorage(test_storage.TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('gcs')
