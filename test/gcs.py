
import test_storage

import storage


class TestGSStorage(test_storage.TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('gcs')
