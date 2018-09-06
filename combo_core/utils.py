import os
import stat
import shutil


class ObjectNotFound(LookupError):
    pass


class MultipleObjectsFound(LookupError):
    pass


def rmtree(top):
    if not os.path.exists(top):
        return
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)

        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def xfilter(func, iterable):
    filtered = list(filter(func, iterable))
    if len(filtered) < 1:
        raise ObjectNotFound('No record found matching the selected filter')
    elif len(filtered) > 1:
        raise MultipleObjectsFound('Multiple records found with the selected filter')

    return filtered[0]


def is_iterable(x):
    return hasattr(x, '__iter__')


def is_in(x, y):
    if is_iterable(y):
        return x == y
    return x in y


def dicts_equal(d1, d2):
    if not d1.keys() == d2.keys():
        return False
    for key in d1.keys():
        if d1[key] != d2[key]:
            return False
    return True
