"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from servers import *


class DependencyBase(object):
    def __init__(self):
        pass

    def clone(self, version, dst_path):
        raise NotImplementedError


class GitDependency(DependencyBase):
    def __init__(self, repo_name):
        DependencyBase.__init__(self)
        self._repo_name = repo_name
        self._url = project_name_to_url(repo_name)
        self._repo = None

    def clone(self, version, dst_path):
        import git

        # Clone the dependency
        self._repo = git.Repo.clone_from(self._url, dst_path)

        # Checkout to the requested commit
        commit_hash = get_commit(self._repo_name, version)
        self._repo.head.reference = commit_hash
        self._repo.head.reset(working_tree=True)

        rmtree(os.path.join(dst_path, ".git"))


class DependencyImport:
    def __init__(self, source):
        self._src = source

        # TODO: Currently source is the "project name", the server converts specifically to URL temporarily
        # assert '.git' in source, "Unsupported source type"
        self._handler = GitDependency(source)

    def clone(self, version, dst_path):
        self._handler.clone(version, dst_path)

