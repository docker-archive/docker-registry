#!/usr/bin/env python

import os
import sys

import simplejson as json

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(root_path, 'lib'))

import storage


store = storage.load()
images_cache = {}
ancestry_cache = {}
dry_run = True


def warning(msg):
    print >>sys.stderr, '# Warning: ' + msg


def get_image_parent(image_id):
    global images_cache
    if image_id in images_cache:
        return images_cache[image_id]
    image_json = os.path.join(store.images, image_id, 'json')
    parent_id = None
    try:
        info = json.loads(store.get_content(image_json))
        if info['id'] != image_id:
            warning('image_id != json image_id for image_id: ' + image_id)
        parent_id = info.get('parent')
    except IOError:
        warning('graph is broken for image_id: {0}'.format(image_id))
    images_cache[image_id] = parent_id
    return parent_id


def create_image_ancestry(image_id):
    global ancestry_cache
    if image_id in ancestry_cache:
        # We already generated the ancestry for that one
        return
    ancestry = [image_id]
    parent_id = image_id
    while True:
        parent_id = get_image_parent(parent_id)
        if not parent_id:
            break
        ancestry.append(parent_id)
        create_image_ancestry(parent_id)
    ancestry_path = os.path.join(store.images, image_id, 'ancestry')
    if dry_run is False:
        store.put_content(ancestry_path, json.dumps(ancestry))
    ancestry_cache[image_id] = True
    print 'Generated ancestry (size: {0}) for image_id: {1}'.format(
            len(ancestry), image_id)


def resolve_all_tags():
    for namespace in store.list_directory(store.repositories):
        for repos in store.list_directory(namespace):
            for tag in store.list_directory(repos):
                yield store.get_content(tag)


def is_invalid_image(image_id):
    try:
        image_json = os.path.join(store.images, image_id, 'json')
        info = json.loads(store.get_content(image_json))
        image_id_json = info['id']
        if image_id_json != image_id:
            return True
    except (IOError, json.JSONDecodeError):
        return True
    return False


def find_invalid_and_orphans():
    for image in store.list_directory(store.images):
        image_id = image.split('/').pop()
        if is_invalid_image(image_id):
            warning('{0} is broken'.format(image_id))
        elif image_id not in ancestry_cache:
            warning('{0} is orphan'.format(image_id))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--seriously':
        dry_run = False
    for image_id in resolve_all_tags():
        create_image_ancestry(image_id)
    find_invalid_and_orphans()
    if dry_run:
        print '-------'
        print '/!\ No modification has been made (dry-run)'
        print '/!\ In order to apply the changes, re-run with:'
        print '$ {0} --seriously'.format(sys.argv[0])
    else:
        print '# Changes applied.'
