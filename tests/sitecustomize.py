# -*- coding: utf-8 -*-

'''This is a dirty hack in order to have gevent monkeying kick in before
nose and avoid the dreaded key error'''

# Prevent gevent monkeypatching used on lib/storage/s3 to throw KeyError
# exception. Should be loaded as early as posible:
#   http://stackoverflow.com/questions/8774958
import gevent.monkey
gevent.monkey.patch_thread()
