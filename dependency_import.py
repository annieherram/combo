"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from version2commit import *


class DependencyBase(object):
    def __init__(self):
        pass

    def clone(self, version, dst_path):
        raise NotImplementedError


class GitDependency(DependencyBase):
    def __init__(self, url):
        DependencyBase.__init__(self)
        self._url = url
        self._repo = None

    def clone(self, version, dst_path):
        import git

        # Clone the dependency
        self._repo = git.Repo.clone_from(self._url, dst_path)

        # Checkout to the requested commit
        commit_hash = version2commit(self._repo, version)
        self._repo.head.reference = commit_hash

        rmtree(os.path.join(dst_path, ".git"))


class DependencyImport:
    def __init__(self, source):
        self._src = source

        assert '.git' in source, "Unsupported source type"
        self._handler = GitDependency(source)

    def clone(self, version, dst_path):
        self._handler.clone(version, dst_path)

