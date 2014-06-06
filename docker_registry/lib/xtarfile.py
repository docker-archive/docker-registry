'''
This is __proc_pax from ./Lib/tarfile.py from v2.7.6
catching raw (non-utf8) bytes to support some xattr headers in tar archives

This is for the use-case of reading the tar archive, not for the use case of
interacting with inodes on the filesystem that have xattr's.
 -- vbatts
'''

import re
import tarfile


def _proc_pax(self, filetar):
    """Process an extended or global header as described in
      POSIX.1-2001.
   """
    # Read the header information.
    buf = filetar.fileobj.read(self._block(self.size))

    # A pax header stores supplemental information for either
    # the following file (extended) or all following files
    # (global).
    if self.type == tarfile.XGLTYPE:
        pax_headers = filetar.pax_headers
    else:
        pax_headers = filetar.pax_headers.copy()

    # Parse pax header information. A record looks like that:
    # "%d %s=%s\n" % (length, keyword, value). length is the size
    # of the complete record including the length field itself and
    # the newline. keyword and value are both UTF-8 encoded strings.
    regex = re.compile(r"(\d+) ([^=]+)=", re.U)
    pos = 0
    while True:
        match = regex.match(buf, pos)
        if not match:
            break

        length, keyword = match.groups()
        length = int(length)
        value = buf[match.end(2) + 1:match.start(1) + length - 1]

        try:
            keyword = keyword.decode("utf8")
        except Exception:
            # just leave the raw bytes
            pass

        try:
            value = value.decode("utf8")
        except Exception:
            # just leave the raw bytes
            pass

        pax_headers[keyword] = value
        pos += length

    # Fetch the next header.
    try:
        next = self.fromtarfile(filetar)
    except tarfile.HeaderError:
        raise tarfile.SubsequentHeaderError("missing or bad subsequent header")

    if self.type in (tarfile.XHDTYPE, tarfile.SOLARIS_XHDTYPE):
        # Patch the TarInfo object with the extended header info.
        next._apply_pax_info(pax_headers, filetar.encoding, filetar.errors)
        next.offset = self.offset

        if "size" in pax_headers:
            # If the extended header replaces the size field,
            # we need to recalculate the offset where the next
            # header starts.
            offset = next.offset_data
            if next.isreg() or next.type not in tarfile.SUPPORTED_TYPES:
                offset += next._block(next.size)
            filetar.offset = offset

    return next

tarfile.TarInfo._proc_pax = _proc_pax
