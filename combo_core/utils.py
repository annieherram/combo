import os
import hashlib
import stat
import shutil


class ObjectNotFound(LookupError):
    pass


class MultipleObjectsFound(LookupError):
    pass





class Directory(object):
    def __init__(self, path):
        self.path = path

    def exists(self):
        return os.path.exists(self.path)

    def join(self, *paths):
        return Directory(os.path.join(self.path, *paths))

    def copy_to(self, dst, symlinks=False, ignore=None):
        if not self.exists():
            raise BaseException()  # TODO

        for item in os.listdir(self.path):
            if not os.path.exists(dst):
                os.makedirs(dst)

            s = os.path.join(self.path, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

        return Directory(dst)

    def size(self):
        total_size = 0

        for dirpath, dirnames, filenames in os.walk(self.path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def remove(self):
        if not self.exists():
            return
        for root, dirs, files in os.walk(self.path, topdown=False):
            for name in files:
                filename = os.path.join(root, name)
                os.chmod(filename, stat.S_IWUSR)
                os.remove(filename)
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.path)

    def __len__(self):
        return self.size()

    def __hash__(self):
        import hashlib, os
        sha_hash = hashlib.md5()
        if not self.exists():
            raise BaseException()  # TODO

        for root, dirs, files in os.walk(self.path):
            for names in files:
                with open(os.path.join(root, names), 'rb') as f:
                    buf = f.read()
                    sha_hash.update(hashlib.md5(buf).hexdigest())

        return sha_hash.hexdigest()


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
