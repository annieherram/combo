"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from version2commit import *


class DependencyBase(object):
    def __init__(self):
        pass

    def clone(self, version):
        raise NotImplementedError


class GitDependency(DependencyBase):
    def __init__(self, url):
        DependencyBase.__init__(self)
        self._url = url
        self._repo = None

    def clone(self, version):
        commit = version2commit(self._repo, self._url, version)
        print 'Hello World!'


class DependencyImport:
    def __init__(self, source):
        self._src = source

        assert '.git' in source, "Unsupported source type"
        self._handler = GitDependency(source)

    def clone(self, version):
        pass

