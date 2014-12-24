from __future__ import print_function

import sys
py3 = sys.version_info >= (3,0)

import io
import re
import os
import itertools
import functools


TEMPLATE_PATH = ['.', './views']
TEMPLATE_EXTS = ['', '.tpl', '.html']


def render(code, **kwargs):
    expre = re.compile(r'<%=\s*(.*?)\s*%>', re.DOTALL)
    blkre = re.compile(r'<%=?\s*(.*?)\s*%>', re.DOTALL)
    match = blkre.search(code)
    while match:
        statement = match.group(1)
        if expre.match(match.group()):
            result = eval(statement, {}, kwargs)
            code = '{0}{1}{2}'.format(code[:match.start()], result, code[match.end():])
        else:
            result = io.StringIO() if py3 else io.BytesIO()
            namespace = {'print': result.write,
                         'include': functools.partial(_include, namespace=kwargs, print=result.write)}
            exec(statement, namespace, kwargs)
            code = '{0}{1}{2}'.format(code[:match.start()], result.getvalue(), code[match.end():])
        match = blkre.search(code)
    return code


def _include(template, namespace, print=print):
    code = _loadtpl(template)
    print(render(code, **namespace))


def _loadtpl(template):
    for path, ext in itertools.product(TEMPLATE_PATH, TEMPLATE_EXTS):
        source = os.path.join(path, '{0}{1}'.format(template, ext))
        if os.path.exists(source):
            break
    else:
        raise RuntimeError, 'Template file not found'
    mode = 'r' if py3 else 'rb'
    with open(source, mode) as f:
        return f.read()


def view(template):
    code = _loadtpl(template)
    def wrapper(func):
        def servetpl(*args, **kwargs):
            namespace = func(*args, **kwargs)
            return render(code, **namespace)
        return servetpl
    return wrapper


def template(template, **kwargs):
    code = _loadtpl(template)
    return render(code, **kwargs)
