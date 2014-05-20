#!/usr/bin/env python

from __future__ import print_function

import hashlib
import sys

import simplejson as json

from docker_registry.core import exceptions
import docker_registry.storage as storage


store = storage.load()
images_cache = {}
ancestry_cache = {}
dry_run = True


def warning(msg):
    print('# Warning: ' + msg, file=sys.stderr)


def get_image_parent(image_id):
    if image_id in images_cache:
        return images_cache[image_id]
    image_json = store.image_json_path(image_id)
    parent_id = None
    try:
        # Note(dmp): unicode patch
        info = store.get_json(image_json)
        if info['id'] != image_id:
            warning('image_id != json image_id for image_id: ' + image_id)
        parent_id = info.get('parent')
    except exceptions.FileNotFoundError:
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
    ancestry_path = store.image_ancestry_path(image_id)
    if dry_run is False:
        if not store.exists(ancestry_path):
            store.put_content(ancestry_path, json.dumps(ancestry))
    ancestry_cache[image_id] = True
    print('Generated ancestry (size: {0}) '
          'for image_id: {1}'.format(len(ancestry), image_id))


def resolve_all_tags():
    for namespace in store.list_directory(store.repositories):
        for repos in store.list_directory(namespace):
            try:
                for tag in store.list_directory(repos):
                    fname = tag.split('/').pop()
                    if not fname.startswith('tag_'):
                        continue
                    yield store.get_content(tag)
            except exceptions.FileNotFoundError:
                pass


def compute_image_checksum(image_id, json_data):
    layer_path = store.image_layer_path(image_id)
    if not store.exists(layer_path):
        warning('{0} is broken (no layer)'.format(image_id))
        return
    print('Writing checksum for {0}'.format(image_id))
    if dry_run:
        return
    h = hashlib.sha256(json_data + '\n')
    for buf in store.stream_read(layer_path):
        h.update(buf)
    checksum = 'sha256:{0}'.format(h.hexdigest())
    checksum_path = store.image_checksum_path(image_id)
    store.put_content(checksum_path, checksum)


def load_image_json(image_id):
    try:
        json_path = store.image_json_path(image_id)
        json_data = store.get_content(json_path)
        # Note(dmp): unicode patch
        info = json.loads(json_data.decode('utf8'))
        if image_id != info['id']:
            warning('{0} is broken (json\'s id mismatch)'.format(image_id))
            return
        return json_data
    except (IOError, exceptions.FileNotFoundError, json.JSONDecodeError):
        warning('{0} is broken (invalid json)'.format(image_id))


def compute_missing_checksums():
    for image in store.list_directory(store.images):
        image_id = image.split('/').pop()
        if image_id not in ancestry_cache:
            warning('{0} is orphan'.format(image_id))
        json_data = load_image_json(image_id)
        if not json_data:
            continue
        checksum_path = store.image_checksum_path(image_id)
        if store.exists(checksum_path):
            # Checksum already there, skipping
            continue
        compute_image_checksum(image_id, json_data)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--seriously':
        dry_run = False
    for image_id in resolve_all_tags():
        create_image_ancestry(image_id)
    compute_missing_checksums()
    if dry_run:
        print('-------')
        print('/!\ No modification has been made (dry-run)')
        print('/!\ In order to apply the changes, re-run with:')
        print('$ {0} --seriously'.format(sys.argv[0]))
    else:
        print('# Changes applied.')
