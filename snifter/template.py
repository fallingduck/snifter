from __future__ import print_function

import sys
py3 = sys.version_info >= (3,0)

import io
import re


def template(code, **kwargs):
    expre = re.compile(r'<%=\s*(.*?)\s*%>', re.DOTALL)
    blkre = re.compile(r'<%=?\s*(.*?)\s*%>', re.DOTALL)
    for match in blkre.finditer(code):
        statement = match.group(1)
        if expre.match(match.group()):
            result = eval(statement, {}, kwargs)
            code = '{0}{1}{2}'.format(code[:match.start()], result, code[match.end():])
        else:
            result = io.StringIO() if py3 else io.BytesIO()
            exec(statement, {'print': result.write}, kwargs)
            code = '{0}{1}{2}'.format(code[:match.start()], result.getvalue(), code[match.end():])
    return code
