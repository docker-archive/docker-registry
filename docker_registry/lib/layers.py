# -*- coding: utf-8 -*-

import logging
import tempfile

import backports.lzma as lzma
from docker_registry.core import compat
json = compat.json

from .. import storage
from . import cache
from . import rqueue
# this is our monkey patched snippet from python v2.7.6 'tarfile'
# with xattr support
from .xtarfile import tarfile


store = storage.load()

FILE_TYPES = {
    tarfile.REGTYPE: 'f',
    tarfile.AREGTYPE: 'f',
    tarfile.LNKTYPE: 'l',
    tarfile.SYMTYPE: 's',
    tarfile.CHRTYPE: 'c',
    tarfile.BLKTYPE: 'b',
    tarfile.DIRTYPE: 'd',
    tarfile.FIFOTYPE: 'i',
    tarfile.CONTTYPE: 't',
    tarfile.GNUTYPE_LONGNAME: 'L',
    tarfile.GNUTYPE_LONGLINK: 'K',
    tarfile.GNUTYPE_SPARSE: 'S',
}

logger = logging.getLogger(__name__)

# queue for requesting diff calculations from workers
diff_queue = rqueue.CappedCollection(cache.redis_conn, "diff-worker", 1024)


def enqueue_diff(image_id):
    try:
        if cache.redis_conn:
            diff_queue.push(image_id)
    except cache.redis.exceptions.ConnectionError as e:
        logger.warning("Diff queue: Redis connection error: {0}".format(e))


def generate_ancestry(image_id, parent_id=None):
    if not parent_id:
        store.put_content(store.image_ancestry_path(image_id),
                          json.dumps([image_id]))
        return
    # Note(dmp): unicode patch
    data = store.get_json(store.image_ancestry_path(parent_id))
    data.insert(0, image_id)
    # Note(dmp): unicode patch
    store.put_json(store.image_ancestry_path(image_id), data)


class Archive(lzma.LZMAFile):
    """file-object wrapper for decompressing xz compressed tar archives
    This class wraps a file-object that contains tar archive data. The data
    will be optionally decompressed with lzma/xz if found to be a compressed
    archive.
    The file-object itself must be seekable.
    """

    def __init__(self, *args, **kwargs):
        super(Archive, self).__init__(*args, **kwargs)
        self.compressed = True

    def _proxy(self, method, *args, **kwargs):
        if not self.compressed:
            return getattr(self._fp, method)(*args, **kwargs)
        if self.compressed:
            previous = self._fp.tell()
            try:
                return getattr(super(Archive, self), method)(*args, **kwargs)
            except lzma._lzma.LZMAError:
                self._fp.seek(previous)
                self.compressed = False
                return getattr(self._fp, method)(*args, **kwargs)

    def tell(self):
        return self._proxy('tell')

    def close(self):
        return self._proxy('close')

    def seek(self, offset, whence=0):
        return self._proxy('seek', offset, whence)

    def read(self, size=-1):
        return self._proxy('read', size)

    def _check_can_seek(self):
        return True

    def seekable(self):
        return True

    def readable(self):
        return True


class TarFilesInfo(object):

    def __init__(self):
        self.infos = []

    def append(self, member):
        info = serialize_tar_info(member)
        if info is not None:
            self.infos.append(info)

    def json(self):
        return json.dumps(self.infos)


def serialize_tar_info(tar_info):
    '''serialize a tarfile.TarInfo instance
    Take a single tarfile.TarInfo instance and serialize it to a
    tuple. Consider union whiteouts by filename and mark them as
    deleted in the third element. Don't include union metadata
    files.
    '''
    is_deleted = False
    filename = tar_info.name

    # notice and strip whiteouts
    if filename == ".":
        filename = '/'

    if filename.startswith("./"):
        filename = "/" + filename[2:]

    if filename.startswith("/.wh."):
        filename = "/" + filename[5:]
        is_deleted = True

    if filename.startswith("/.wh."):
        return None

    return (
        filename,
        FILE_TYPES.get(tar_info.type, 'u'),
        is_deleted,
        tar_info.size,
        tar_info.mtime,
        tar_info.mode,
        tar_info.uid,
        tar_info.gid,
    )


def read_tarfile(tar_fobj):
    # iterate over each file in the tar and then serialize it
    return [
        i for i in [serialize_tar_info(m) for m in tar_fobj.getmembers()]
        if i is not None
    ]


def get_image_files_cache(image_id):
    image_files_path = store.image_files_path(image_id)
    if store.exists(image_files_path):
        return store.get_content(image_files_path)


def set_image_files_cache(image_id, files_json):
    image_files_path = store.image_files_path(image_id)
    store.put_content(image_files_path, files_json)


def get_image_files_from_fobj(layer_file):
    '''get files from open file-object containing a layer

    Download the specified layer and determine the file contents.
    Alternatively, process a passed in file-object containing the
    layer data.

    '''
    layer_file.seek(0)
    archive_file = Archive(layer_file)
    tar_file = tarfile.open(fileobj=archive_file)
    files = read_tarfile(tar_file)
    return files


def get_image_files_json(image_id):
    '''return json file listing for given image id
    Download the specified layer and determine the file contents.
    Alternatively, process a passed in file-object containing the
    layer data.
    '''
    files_json = get_image_files_cache(image_id)
    if files_json:
        return files_json

    # download remote layer
    image_path = store.image_layer_path(image_id)
    with tempfile.TemporaryFile() as tmp_fobj:
        for buf in store.stream_read(image_path):
            tmp_fobj.write(buf)
        tmp_fobj.seek(0)
        # decompress and untar layer
        files_json = json.dumps(get_image_files_from_fobj(tmp_fobj))
    set_image_files_cache(image_id, files_json)
    return files_json


def get_file_info_map(file_infos):
    '''convert a list of file info tuples to dictionaries
    Convert a list of layer file info tuples to a dictionary using the
    first element (filename) as the key.
    '''
    return dict((file_info[0], file_info[1:]) for file_info in file_infos)


def get_image_diff_cache(image_id):
    image_diff_path = store.image_diff_path(image_id)
    if store.exists(image_diff_path):
        return store.get_content(image_diff_path)


def set_image_diff_cache(image_id, diff_json):
    image_diff_path = store.image_diff_path(image_id)
    store.put_content(image_diff_path, diff_json)


def get_image_diff_json(image_id):
    '''get json describing file differences in layer
    Calculate the diff information for the files contained within
    the layer. Return a dictionary of lists grouped by whether they
    were deleted, changed or created in this layer.

    To determine what happened to a file in a layer we walk backwards
    through the ancestry until we see the file in an older layer. Based
    on whether the file was previously deleted or not we know whether
    the file was created or modified. If we do not find the file in an
    ancestor we know the file was just created.

        - File marked as deleted by union fs tar: DELETED
        - Ancestor contains non-deleted file:     CHANGED
        - Ancestor contains deleted marked file:  CREATED
        - No ancestor contains file:              CREATED
    '''

    # check the cache first
    diff_json = get_image_diff_cache(image_id)
    if diff_json:
        return diff_json

    # we need all ancestral layers to calculate the diff
    ancestry_path = store.image_ancestry_path(image_id)
    # Note(dmp): unicode patch
    ancestry = store.get_json(ancestry_path)[1:]
    # grab the files from the layer
    # Note(dmp): unicode patch NOT applied - implications not clear
    files = json.loads(get_image_files_json(image_id))
    # convert to a dictionary by filename
    info_map = get_file_info_map(files)

    deleted = {}
    changed = {}
    created = {}

    # walk backwards in time by iterating the ancestry
    for id in ancestry:
        # get the files from the current ancestor
        # Note(dmp): unicode patch NOT applied - implications not clear
        ancestor_files = json.loads(get_image_files_json(id))
        # convert to a dictionary of the files mapped by filename
        ancestor_map = get_file_info_map(ancestor_files)
        # iterate over each of the top layer's files
        for filename, info in info_map.items():
            ancestor_info = ancestor_map.get(filename)
            # if the file in the top layer is already marked as deleted
            if info[1]:
                deleted[filename] = info
                del info_map[filename]
            # if the file exists in the current ancestor
            elif ancestor_info:
                # if the file was marked as deleted in the ancestor
                if ancestor_info[1]:
                    # is must have been just created in the top layer
                    created[filename] = info
                else:
                    # otherwise it must have simply changed in the top layer
                    changed[filename] = info
                del info_map[filename]
    created.update(info_map)

    # return dictionary of files grouped by file action
    diff_json = json.dumps({
        'deleted': deleted,
        'changed': changed,
        'created': created,
    })

    # store results in cache
    set_image_diff_cache(image_id, diff_json)

    return diff_json
