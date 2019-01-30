from combo_core import *
from .compat import string_types
from semantic_version import *


class IncompatibleVersions(ComboException):
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
                self.version = Version(tuple_or_str)
            elif is_iterable(tuple_or_str):
                assert all(type(x) is int for x in tuple_or_str), 'Invalid version iterable: {}'.format(tuple_or_str)
                self._prefix = self.default_prefix
                self.version = Version('.'.join(tuple_or_str))
            else:
                raise TypeError('Invalid version type "{}" for parameter: {}'.format(type(tuple_or_str), tuple_or_str))
        except BaseException as e:
            raise InvalidVersionNumber(tuple_or_str, prefix, e)

    def as_tuple(self):
        return tuple(self.version)

    def as_string(self):
        return self._prefix + str(self.version)

    @staticmethod
    def validate(tuple_or_str, prefix=default_prefix):
        VersionNumber(tuple_or_str, prefix)

    @staticmethod
    def compatible(*versions):
        if not all(isinstance(ver, VersionNumber) for ver in versions):
            raise TypeError('Non version types for: {}'.format(
                filter(lambda ver: not isinstance(ver, VersionNumber), versions)))

        minimal_version = '^' + str(min(versions))
        return all(Spec(minimal_version).match(ver) for ver in versions)

    def __str__(self):
        return self.as_string()

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self.version < other.version

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self.version == other.version

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.version)

    @staticmethod
    def _remove_prefix(string, prefix):
        assert string.startswith(prefix), 'String {} does not start with prefix {}'.format(string, prefix)
        return string[len(prefix):]

