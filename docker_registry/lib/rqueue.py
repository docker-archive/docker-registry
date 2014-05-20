# -*- coding: utf-8 -*-

# this module is a slight modification of Ted Nyman's QR
# https://raw.github.com/tnm/qr/master/qr.py

import logging

from docker_registry.core import compat
json = compat.json


class NullHandler(logging.Handler):
    """A logging handler that discards all logging records."""
    def emit(self, record):
        pass


# Clients can add handlers if they are interested.
log = logging.getLogger('qr')
log.addHandler(NullHandler())


class worker(object):
    def __init__(self, q, *args, **kwargs):
        self.q = q
        self.err = kwargs.get('err', None)
        self.args = args
        self.kwargs = kwargs

    def __call__(self, f):
        def wrapped():
            while True:
                # Blocking pop
                next = self.q.pop(block=True)
                if not next:
                    continue
                try:
                    # Try to execute the user's callback.
                    f(next, *self.args, **self.kwargs)
                except Exception as e:
                    try:
                        # Failing that, let's call the user's
                        # err-back, which we should keep from
                        # ever throwing an exception
                        self.err(e, *self.args, **self.kwargs)
                    except Exception:
                        pass
        return wrapped


class BaseQueue(object):
    """Base functionality common to queues."""
    def __init__(self, r_conn, key, **kwargs):
        self.serializer = json
        self.redis = r_conn
        self.key = key

    def __len__(self):
        """Return the length of the queue."""
        return self.redis.llen(self.key)

    def __getitem__(self, val):
        """Get a slice or a particular index."""
        try:
            slice = self.redis.lrange(self.key, val.start, val.stop - 1)
            return [self._unpack(i) for i in slice]
        except AttributeError:
            return self._unpack(self.redis.lindex(self.key, val))
        except Exception as e:
            log.error('Get item failed ** %s' % repr(e))
            return None

    def _pack(self, val):
        """Prepares a message to go into Redis."""
        return self.serializer.dumps(val, 1)

    def _unpack(self, val):
        """Unpacks a message stored in Redis."""
        try:
            return self.serializer.loads(val)
        except TypeError:
            return None

    def dump(self, fobj):
        """Destructively dump the contents of the queue into fp."""
        next = self.redis.rpop(self.key)
        while next:
            fobj.write(next)
            next = self.redis.rpop(self.key)

    def load(self, fobj):
        """Load the contents of the provided fobj into the queue."""
        try:
            while True:
                val = self._pack(self.serializer.load(fobj))
                self.redis.lpush(self.key, val)
        except Exception:
            return

    def dumpfname(self, fname, truncate=False):
        """Destructively dump the contents of the queue into fname."""
        if truncate:
            with file(fname, 'w+') as f:
                self.dump(f)
        else:
            with file(fname, 'a+') as f:
                self.dump(f)

    def loadfname(self, fname):
        """Load the contents of the contents of fname into the queue."""
        with file(fname) as f:
            self.load(f)

    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline(transaction=False) as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.execute()

    def peek(self):
        """Look at the next item in the queue."""
        return self[-1]

    def elements(self):
        """Return all elements as a Python list."""
        return [self._unpack(o) for o in self.redis.lrange(self.key, 0, -1)]

    def elements_as_json(self):
        """Return all elements as JSON object."""
        return json.dumps(self.elements)

    def clear(self):
        """Removes all the elements in the queue."""
        self.redis.delete(self.key)


class CappedCollection(BaseQueue):
    """a bounded queue
    Implements a capped collection (the collection never
    gets larger than the specified size).
    """

    def __init__(self, r_conn, key, size, **kwargs):
        BaseQueue.__init__(self, r_conn, key, **kwargs)
        self.size = size

    def push(self, element):
        size = self.size
        with self.redis.pipeline() as pipe:
            # ltrim is zero-indexed
            val = self._pack(element)
            pipe = pipe.lpush(self.key, val).ltrim(self.key, 0, size - 1)
            pipe.execute()

    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline() as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.ltrim(self.key, 0, self.size - 1)
            pipe.execute()

    def pop(self, block=False):
        if not block:
            popped = self.redis.rpop(self.key)
        else:
            queue, popped = self.redis.brpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)
