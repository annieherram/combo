import json
from utils import *


class MajorVersionMismatch(Exception):
    pass


class VersionFormatter:
    def __init__(self, prefix_format=''):
        self._prefix = prefix_format

    def get_as_tuple(self, version_str):
        assert version_str[:len(self._prefix)] == self._prefix, \
            "Version string is expected to start with the prefix '{}'".format(version_str)
        return tuple(map(int, version_str[len(self._prefix):].split(".")))

    def is_version(self, tag):
        try:
            self.get_as_tuple(str(tag))
        except (AssertionError, ValueError):
            return False
        return True

    def get_version_tags(self, tags):
        return filter(self.is_version, tags)

    def get_latest_version(self, tags):
        version_tags = self.get_version_tags(tags)
        max_version = max(map(self.get_as_tuple, map(str, version_tags)))
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == max_version, version_tags)

    def get_requested_version(self, tags, requested_version_tuple):
        version_tags = self.get_version_tags(tags)
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == requested_version_tuple, version_tags)

    def get_latest(self, version_strings):
        tuples = map(self.get_as_tuple, version_strings)
        max_version = max(tuples)

        # If there is a dependency with a different major number, raise an error
        if any(version[0] < max_version[0] for version in tuples):
            raise MajorVersionMismatch

        return filter(lambda v: self.get_as_tuple(v) == max_version, version_strings)[0]


def version2commit(repo, name, version_str):
    json_file_name = name + '_versions.json'
    versions_dict = json.load(open(json_file_name, 'r'))

    req_version_tuple = VersionFormatter().get_as_tuple(version_str)
    commit = VersionFormatter(versions_dict['prefix']).get_requested_version(repo.tags, req_version_tuple)

    return commit


