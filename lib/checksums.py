
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
        f = tar.extractfile(member)
        if not f:
            continue
        header = ''
        for field in header_fields:
            value = getattr(member, aliases.get(field, field))
            header += '{0}{1}'.format(field, value)
        hashes.append(sha256_file(f, header))
    tar.close()
    hashes.sort()
    data = json_data + ''.join(hashes)
    tarsum = hashlib.sha256(data).hexdigest()
    return 'tarsum+sha256:{0}'.format(tarsum)


def compute_simple(fp, json_data):
    data = json_data + '\n'
    return 'sha256:{0}'.format(sha256_file(fp, data))
