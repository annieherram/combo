from utils import *


class MajorVersionMismatch(BaseException):
    pass


class Version:
    def __init__(self, tuple_or_str, prefix=''):
        if is_string(tuple_or_str):
            self._prefix = prefix
            self._tup = tuple(map(int, self._remove_prefix(tuple_or_str, prefix).split('.')))
            self.major = self._extract_major(self._tup)
        elif is_iterable(tuple_or_str):
            assert all(type(x) is int for x in tuple_or_str), 'Invalid version iterable: {}'.format(tuple_or_str)
            self._tup = tuple(tuple_or_str)
        else:
            raise TypeError('Invalid version type "{}" for parameter: {}'.format(type(tuple_or_str), tuple_or_str))

    def as_tuple(self):
        return self._tup

    def as_string(self):
        return self._prefix + '.'.join(map(str, self._tup))

    @staticmethod
    def same_major(*args):
        if not all(isinstance(ver, Version) for ver in args):
            raise TypeError('Non version types for: {}'.format(
                filter(lambda ver: not isinstance(ver, Version), args)))

        return all(args[i].major == args[i+1].major for i in range(len(args) - 1))

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        if not self.same_major(self, other):
            raise MajorVersionMismatch(self.as_string(), other.as_string())
        return self._tup < other._tup

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._tup == other._tup

    @staticmethod
    def _extract_major(tup):
        return tup[0]

    @staticmethod
    def _remove_prefix(string, prefix):
        assert string.startswith(prefix), 'String {} does not start with prefix {}'.format(string, prefix)
        return string[len(prefix):]
