import os
import hashlib
import stat
import shutil


class ObjectNotFound(LookupError):
    pass


class MultipleObjectsFound(LookupError):
    pass


class ActionOnNonexistingDirectory(EnvironmentError):
    pass


class Directory(object):
    def __init__(self, path):
        self.path = path.path if isinstance(path, type(self)) else os.path.abspath(path)

    def name(self):
        return os.path.split(self.path)[-1]

    def exists(self):
        return os.path.exists(self.path)

    def is_dir(self):
        return os.path.isdir(self.path)

    def join(self, *paths):
        target_path = os.path.abspath(os.path.join(self.path, *paths))
        return Directory(target_path)

    def sons(self):
        if not self.is_dir():
            return list()
        return [self.join(x) for x in os.listdir(self.path) if self.join(x).is_dir()]

    def up(self):
        return Directory(os.path.dirname(self.path))

    def get_file(self, default_content=''):
        if not self.exists():
            if default_content is None:
                raise EnvironmentError('File {} does not exist'.format(self.path))

            if not self.up().exists():
                os.makedirs(self.up().path)

            with open(self.path, 'w') as f:
                f.write(default_content)

        assert not os.path.isdir(self.path), 'Requested to get directory {} as file'.format(self.path)
        return self.path

    def copy_to(self, dst, symlinks=False, ignore=None):
        if not self.exists():
            raise ActionOnNonexistingDirectory(self.path)

        dst_path = dst.path if isinstance(dst, type(self)) else dst

        for item in os.listdir(self.path):
            if not os.path.exists(dst_path):
                os.makedirs(dst_path)

            s = os.path.join(self.path, item)
            d = os.path.join(dst_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

        return Directory(dst_path)

    def size(self):
        total_size = 0

        for dirpath, dirnames, filenames in os.walk(self.path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def delete(self):
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

    def relative_to(self, other):
        return os.path.relpath(self.path, other.path)

    def get_hash(self):
        sha_hash = hashlib.md5()
        
        if not self.exists():
            raise ActionOnNonexistingDirectory(self.path)

        for root, dirs, files in os.walk(self.path):
            # This is sorted for determined results between all platforms, must be sorted here
            dirs.sort()
            files.sort()

            for names in files:
                file_path = os.path.join(root, names)
                path_to_hash = os.path.relpath(file_path, self.path)
                sha_hash.update(path_to_hash.encode())

                with open(file_path, 'rb') as f:
                    for buf in iter(lambda: f.read(4096), b''):
                        sha_hash.update(buf)

        return sha_hash.hexdigest()

    def __hash__(self):
        # Masking the result to the limit of python's __hash__ function
        return int(self.get_hash(), 16) & 0x7FFFFFFF

    def __str__(self):
        return self.path

    def __eq__(self, other):
        assert isinstance(other, type(self))
        return hash(self) == hash(other)

    def __ne__(self, other):
        return not self == other


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
