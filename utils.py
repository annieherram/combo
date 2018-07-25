import os
import stat


class ObjectNotFound(LookupError):
    pass


class MultipleObjectsFound(LookupError):
    pass


def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def xfilter(func, iterable):
    filtered = filter(func, iterable)
    if len(filtered) < 1:
        raise ObjectNotFound('No record found matching the selected filter')
    elif len(filtered) > 1:
        raise MultipleObjectsFound('Multiple records found with the selected filter')

    return filtered[0]