#!/usr/bin/env python

import sys

import simplejson as json

from docker_registry.core import exceptions
import docker_registry.storage as storage

store = storage.load()


def walk_all_tags():
    for namespace_path in store.list_directory(store.repositories):
        for repos_path in store.list_directory(namespace_path):
            try:
                for tag in store.list_directory(repos_path):
                    fname = tag.split('/').pop()
                    if not fname.startswith('tag_'):
                        continue
                    (namespace, repos) = repos_path.split('/')[-2:]
                    yield (namespace, repos, store.get_content(tag))
            except OSError:
                pass


def walk_ancestry(image_id):
    try:
        # Note(dmp): unicode patch
        ancestry = store.get_json(store.image_ancestry_path(image_id))
        return iter(ancestry)
    except exceptions.FileNotFoundError:
        print('Ancestry file for {0} is missing'.format(image_id))
    return []


def get_image_checksum(image_id):
    checksum_path = store.image_checksum_path(image_id)
    if not store.exists(checksum_path):
        return
    checksum = store.get_content(checksum_path)
    return checksum.strip()


def dump_json(all_repos, all_checksums, filename):
    data = []
    for ((namespace, repos), images) in all_repos.iteritems():
        images_checksums = []
        for i in set(images):
            images_checksums.append({'id': i, 'checksum': all_checksums[i]})
        data.append({
            'namespace': namespace,
            'repository': repos,
            'images': images_checksums
        })
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {0} <output_file>'.format(sys.argv[0]))
        sys.exit(1)
    all_repos = {}
    all_checksums = {}
    for (namespace, repos, image_id) in walk_all_tags():
        key = (namespace, repos)
        if key not in all_repos:
            all_repos[key] = []
        for i in walk_ancestry(image_id):
            all_repos[key].append(i)
            if i in all_checksums:
                continue
            all_checksums[i] = get_image_checksum(i)
    dump_json(all_repos, all_checksums, sys.argv[1])
