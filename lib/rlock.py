# https://gist.github.com/adewes/6103220

from redis import WatchError
import time
 
class LockTimeout(BaseException):
    pass
 
class Lock(object):
 
    """
    Implements a distributed lock using Redis.
    """
 
    def __init__(self, redis, lock_type, key, expires=60, timeout=10):
        self.key = key
        self.lock_type = lock_type
        self.redis = redis
        self.timeout = timeout
        self.expires = expires
 
    def lock_key(self):
        return "%s:locks:%s" % (self.lock_type,self.key)
 
    def __enter__(self):
        timeout = self.timeout
        while timeout >= 0:
            expires = time.time() + self.expires + 1
            pipe = self.redis.pipeline()
            lock_key = self.lock_key()
            pipe.watch(lock_key)
            try:
                lock_value = float(self.redis.get(lock_key))
            except (ValueError,TypeError):
                lock_value = None
            if not lock_value or lock_value < time.time():
                try:
                    pipe.multi()
                    pipe.set(lock_key,expires)
                    pipe.expire(lock_key,self.expires+1)
                    pipe.execute()
                    return expires
                except WatchError:
                    print "Someone tinkered with the lock!"
                    pass
            timeout -= 0.01
            time.sleep(0.01)
        raise LockTimeout("Timeout whilst waiting for lock")
 
    def __exit__(self, exc_type, exc_value, traceback):
        self.redis.delete(self.lock_key())
