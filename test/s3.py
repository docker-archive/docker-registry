
import storage

from .test_storage import TestLocalStorage


class TestS3Storage(TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('s3')
