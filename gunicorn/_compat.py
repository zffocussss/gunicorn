from gunicorn import six


def _check_if_pyc(fname):
    """ Returns True if the extension is .pyc, False if .py and None if otherwise """
    from imp import find_module
    from os.path import realpath, dirname, basename, splitext

    # Normalize the file-path for the find_module()
    filepath = realpath(fname)
    dirpath = dirname(filepath)
    module_name = splitext(basename(filepath))[0]

    # Validate and fetch
    try:
        fileobj, fullpath, (_, _, pytype) = find_module(module_name, [dirpath])

    except ImportError:
        raise IOError("Cannot find config file. Path maybe incorrect! : {0}".format(filepath))

    return (pytype, fileobj, fullpath)


def _get_codeobj(pyfile):
    """ Returns the code object, given a python file """
    from imp import PY_COMPILED, PY_SOURCE

    result, fileobj, fullpath = _check_if_pyc(pyfile)

    # WARNING:
    # fp.read() can blowup if the module is extremely large file.
    # Lookout for overflow errors.
    try:
        data = fileobj.read()
    finally:
        fileobj.close()

    # This is a .pyc file. Treat accordingly.
    if result is PY_COMPILED:
        # .pyc format is as follows:
        # 0 - 4 bytes: Magic number, which changes with each create of .pyc file.
        #              First 2 bytes change with each marshal of .pyc file. Last 2 bytes is "\r\n".
        # 4 - 8 bytes: Datetime value, when the .py was last changed.
        # 8 - EOF: Marshalled code object data.
        # So to get code object, just read the 8th byte onwards till EOF, and
        # UN-marshal it.
        import marshal
        code_obj = marshal.loads(data[8:])

    elif result is PY_SOURCE:
        # This is a .py file.
        code_obj = compile(data, fullpath, 'exec')

    else:
        # Unsupported extension
        raise Exception("Input file is unknown format: {0}".format(fullpath))

    # Return code object
    return code_obj

if six.PY3:
    def execfile_(fname, *args):
        if fname.endswith(".pyc"):
            code = _get_codeobj(fname)
        else:
            code = compile(open(fname, 'rb').read(), fname, 'exec')
        return six.exec_(code, *args)

    def bytes_to_str(b):
        if isinstance(b, six.text_type):
            return b
        return str(b, 'latin1')

    import urllib.parse

    def unquote_to_wsgi_str(string):
        return _unquote_to_bytes(string).decode('latin-1')

    _unquote_to_bytes = urllib.parse.unquote_to_bytes

else:
    def execfile_(fname, *args):
        """ Overriding PY2 execfile() implementation to support .pyc files """
        if fname.endswith(".pyc"):
            return six.exec_(_get_codeobj(fname), *args)
        return execfile(fname, *args)

    def bytes_to_str(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    import urllib
    unquote_to_wsgi_str = urllib.unquote
