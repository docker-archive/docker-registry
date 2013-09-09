
import test_storage

import storage


class TestS3Storage(test_storage.TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('s3')
