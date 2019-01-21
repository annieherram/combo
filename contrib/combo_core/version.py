from combo_core import *
from .compat import string_types


class MajorVersionMismatch(ComboException):
    pass


class InvalidVersionNumber(ComboException):
    def __init__(self, value, *args):
        super(InvalidVersionNumber, self).__init__()
        self._value = value
        self._args = args

    def __str__(self):
        return 'Invalid version number format for "{}"\n'.format(self._value) + str(self._args)


class VersionNumber:
    default_prefix = ''

    def __init__(self, tuple_or_str='1.0', prefix=default_prefix):
        try:
            if isinstance(tuple_or_str, string_types):
                self._prefix = prefix
                self._tup = tuple(map(int, self._remove_prefix(tuple_or_str, prefix).split('.')))
                self.major = self._extract_major(self._tup)
            elif is_iterable(tuple_or_str):
                assert all(type(x) is int for x in tuple_or_str), 'Invalid version iterable: {}'.format(tuple_or_str)
                self._prefix = self.default_prefix
                self._tup = tuple(tuple_or_str)
            else:
                raise TypeError('Invalid version type "{}" for parameter: {}'.format(type(tuple_or_str), tuple_or_str))
        except BaseException as e:
            raise InvalidVersionNumber(tuple_or_str, prefix, e)

    def as_tuple(self):
        return self._tup

    def as_string(self):
        return self._prefix + '.'.join(map(str, self._tup))

    @staticmethod
    def validate(tuple_or_str, prefix=default_prefix):
        VersionNumber(tuple_or_str, prefix)

    @staticmethod
    def same_major(*args):
        if not all(isinstance(ver, VersionNumber) for ver in args):
            raise TypeError('Non version types for: {}'.format(
                filter(lambda ver: not isinstance(ver, VersionNumber), args)))

        return len(set(ver.major for ver in args)) <= 1

    def __str__(self):
        return self.as_string()

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self._tup < other._tup

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self._tup == other._tup

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._tup)

    @staticmethod
    def _extract_major(tup):
        return tup[0]

    @staticmethod
    def _remove_prefix(string, prefix):
        assert string.startswith(prefix), 'String {} does not start with prefix {}'.format(string, prefix)
        return string[len(prefix):]
