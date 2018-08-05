from __future__ import print_function
from version import *


class ComboDep:
    def __init__(self, project_name, version):
        self.name = project_name
        self.version = version if isinstance(version, Version) else Version(version)

    def as_tuple(self):
        return self.name, self.version

    def __str__(self):
        return "Project name: {}\n" \
               "Version number: {}".format(self.name, self.version)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Type of {} should be {}'.format(other, type(self)))
        return self.version < other.version


if __name__ == '__main__':
    first = ComboDep(1, 2)
    print(first)
    second = ComboDep(*first.as_tuple())
    print(second)
    third = ComboDep(3, 4)
    d = {first: 'a', third: 'b'}

    print(first in d, second in d)
    print(first == second)
    print(d[second])
    print(d[ComboDep(3, 4)])

