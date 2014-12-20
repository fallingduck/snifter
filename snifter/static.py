import mimetypes
import os
import time
from .error import HTTPError
from .utils import parse_date, parse_range_header, file_iter_range


def static_file(request, response, filename, root, mimetype=None, download=False, charset='UTF-8'):
    """Adapted from Bottle"""
    root = os.path.abspath(root)
    filename = os.path.abspath(os.path.join(root, filename))

    if not filename.startswith(root):
        raise HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        raise HTTPError(403, "Access denied.")

    if mimetype is None:
        if download and download is not True:
            mimetype, encoding = mimetypes.guess_type(download)
        else:
            mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'
        if encoding is not None:
            response['Content-encoding'] = encoding

    if mimetype[:5] == 'text/' and charset and 'charset' not in mimetype:
        mimetype = '{0}; charset={1}'.format(mimetype, charset)
    response['Content-type'] = mimetype

    if download:
        download = os.path.basename(filename if download is True else download)
        response['Content-disposition'] = 'attachment; filename="{0}"'.format(download)

    stats = os.stat(filename)
    clen = stats.st_size
    response['Content-length'] = str(clen)
    last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(stats.st_mtime))
    response['Last-modified'] = last_modified

    ims = request.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        response['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        raise HTTPError(304)

    body = open(filename, 'rb')
    response["Accept-ranges"] = "bytes"
    if 'HTTP_RANGE' in request:
        ranges = list(parse_range_header(request['HTTP_RANGE'], clen))
        if not ranges:
            raise HTTPError(416, "Requested Range Not Satisfiable")
        offset, end = ranges[0]
        response["Content-range"] = 'bytes {0}-{1}/{2}'.format(offset, end-1, clen)
        response["Content-length"] = str(end-offset)
        body = file_iter_range(body, offset, end-offset)
        response.set_status(206)
        return body
    return body
