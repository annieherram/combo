from __future__ import print_function
from version import *


class ComboRoot:
    def __init__(self):
        self.name = 'Root'

    def __str__(self):
        return self.name


class ComboDep:
    def __init__(self, project_name, version):
        self.name = project_name
        self.version = version if isinstance(version, VersionNumber) else VersionNumber(version)

    def as_tuple(self):
        return self.name, self.version

    def normalized_name_dir(self):
        return self.name.lower().replace(' ', '_')

    def normalized_version_dir(self):
        return str(self.version).replace('.', '_')

    def __str__(self):
        return "({}, v{})".format(self.name, str(self.version))

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self.version < other.version
