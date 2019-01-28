from __future__ import print_function
from .version import *


class ComboNode(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class ComboRoot(ComboNode):
    def __init__(self):
        super(ComboRoot, self).__init__('Root')


class ComboDep(ComboNode):
    def __init__(self, project_name, version):
        super(ComboDep, self).__init__(project_name)
        self.version = version if isinstance(version, VersionNumber) else VersionNumber(version)

    def as_tuple(self):
        return self.name, self.version

    @staticmethod
    def normalize_name_dir(name):
        return name.lower().replace(' ', '_')

    @staticmethod
    def normalize_version_dir(version):
        return str(version).replace('.', '_')

    def normalized_name_dir(self):
        return self.normalize_name_dir(self.name)

    def normalized_version_dir(self):
        return self.normalize_version_dir(self.version)

    def __str__(self):
        return "({}, v{})".format(self.name, str(self.version))

    @staticmethod
    def destring(str):
        splitted = str.split(', v')
        name = splitted[0][1:]
        version = VersionNumber(splitted[1][:-1])
        return ComboDep(name, version)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self.version < other.version
