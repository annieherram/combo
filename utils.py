import os
import stat


class MajorVersionMismatch(BaseException):
    pass


class VersionFormatter:
    def __init__(self, prefix_format=''):
        self._prefix = prefix_format

    def get_as_tuple(self, version_str):
        assert version_str.startswith(self._prefix), \
            'Version string is expected to start with the prefix "{}"'.format(version_str)
        return tuple(map(int, version_str[len(self._prefix):].split(".")))

    def get_latest(self, version_strings):
        tuples = map(self.get_as_tuple, version_strings)
        max_version = max(tuples)

        # If there is a dependency with a different major number, raise an error
        # TODO: Remove comment
        # if any(version[0] < max_version[0] for version in tuples):
        #     raise MajorVersionMismatch

        return filter(lambda v: self.get_as_tuple(v) == max_version, version_strings)[0]


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