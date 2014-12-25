import email.utils
import collections
import time
import cgi

from .core import py3


if py3:
    def parse_return(content):
        if isinstance(content, str):
            content = content.encode('utf-8', 'xmlcharrefreplace')
        if isinstance(content, bytes):
            return (content,)
        elif isinstance(content, collections.Iterable):
            return (i.encode('utf-8', 'xmlcharrefreplace') for i in content)
        else:
            return ''
else:
    def parse_return(content):
        if isinstance(content, unicode):
            content = content.encode('utf-8', 'xmlcharrefreplace')
        if isinstance(content, str):
            return (content,)
        elif isinstance(content, collections.Iterable):
            return (i.encode('utf-8', 'xmlcharrefreplace') for i in content)
        else:
            return ''


def parse_date(ims):
    """Adapted from Bottle"""
    try:
        ts = email.utils.parsedate_tz(ims)
        return time.mktime(ts[:8] + (0,)) - (ts[9] or 0) - time.timezone
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def parse_range_header(header, maxlen=0):
    """Adapted from Bottle"""
    if not header or header[:6] != 'bytes=': return
    ranges = [r.split('-', 1) for r in header[6:].split(',') if '-' in r]
    for start, end in ranges:
        try:
            if not start:  # bytes=-100    -> last 100 bytes
                start, end = max(0, maxlen-int(end)), maxlen
            elif not end:  # bytes=100-    -> all but the first 99 bytes
                start, end = int(start), maxlen
            else:          # bytes=100-200 -> bytes 100-200 (inclusive)
                start, end = int(start), min(int(end)+1, maxlen)
            if 0 <= start < end <= maxlen:
                yield start, end
        except ValueError:
            pass


def file_iter_range(fp, offset, bytes_, maxread=1024*1024):
    """Adapted from Bottle"""
    fp.seek(offset)
    while bytes_ > 0:
        part = fp.read(min(bytes_, maxread))
        if not part: break
        bytes_ -= len(part)
        yield part


class FieldStorage(cgi.FieldStorage):
    def get(self, key):
        try:
            return self[key].value
        except KeyError:
            return None
