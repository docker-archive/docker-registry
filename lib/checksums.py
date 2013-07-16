
import hashlib
import tarfile


TarError = tarfile.TarError


def sha256_file(fp, data=None):
    h = hashlib.sha256(data or '')
    while True:
        buf = fp.read(4096)
        if not buf:
            break
        h.update(buf)
    return h.hexdigest()


def sha256_string(s):
    return hashlib.sha256(s).hexdigest()


def compute_tarsum(fp, json_data):
    header_fields = ('name', 'mode', 'uid', 'gid', 'size', 'mtime',
                     'typeflag', 'linkname', 'uname', 'gname', 'devmajor',
                     'devminor')
    aliases = {
        'typeflag': 'type'
    }
    tar = tarfile.open(mode='r:*', fileobj=fp)
    hashes = []
    for member in tar:
        header = ''
        for field in header_fields:
            value = getattr(member, aliases.get(field, field))
            header += '{0}{1}'.format(field, value)
        h = None
        try:
            f = tar.extractfile(member)
            if f:
                h = sha256_file(f, header)
            else:
                h = sha256_string(header)
        except KeyError:
            h = sha256_string(header)
        hashes.append(h)
    tar.close()
    hashes.sort()
    data = json_data + ''.join(hashes)
    return 'tarsum+sha256:{0}'.format(sha256_string(data))


def compute_simple(fp, json_data):
    data = json_data + '\n'
    return 'sha256:{0}'.format(sha256_file(fp, data))
