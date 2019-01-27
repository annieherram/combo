from combo_core import *
import git
import gc
import os


class ReferenceNotFound(ComboException):
    pass


class GitRepo:
    def __init__(self, local_path):
        self.local_path = Directory(local_path)
        self._git_dir = self.local_path.join('.git')

        self._loaded = False
        self._repo = None
        self._tags = None

        if self._git_dir.exists():
            self.load()

    def empty(self):
        if not self.local_path.exists():
            return True
        return len(os.listdir(self.local_path.path)) == 0

    def load(self):
        assert self._git_dir.exists(), 'Trying to load a non existing git repository'

        self._repo = git.Repo(self._git_dir.path)
        self._loaded = True

    def clone(self, remote_url, ref=None):
        if not self.empty():
            raise EnvironmentError()

        if not self.local_path.exists():
            os.makedirs(self.local_path.path)

        # TODO: Add timeout. Fix 'local_projects.json' file in case of timeout before exiting
        self._repo = git.Repo.clone_from(remote_url, self.local_path.path)
        self._loaded = True

        if ref:
            self.checkout(ref)

    def remote_url(self, remote_name):
        assert self._loaded, 'Trying to get remote URL of a repository which was not loaded'
        remote = xfilter(lambda r: r.name == remote_name, self._repo.remotes)
        assert len(list(remote.urls)) > 0, 'No urls for remote {}'.format(remote_name)

        return next(remote.urls)

    def commit_hash(self):
        assert self._loaded, 'Trying to get a commit hash of a repository which was not loaded'
        commit_hash = str(self._repo.head.commit)
        return commit_hash

    def details(self):
        return {'url': self.remote_url('origin'), 'commit_hash': self.commit_hash()}

    def checkout(self, ref):
        try:
            self._repo.head.reference = ref
        except ValueError as e:
            raise ReferenceNotFound(self._git_dir, e)

        self._repo.head.reset(working_tree=True)

    def tags(self):
        self._tags = self._repo.tags
        return self._tags

    def close(self):
        del self._tags, self._repo
        gc.collect()

        if self._git_dir.exists():
            self._git_dir.delete()

    def delete(self):
        self.close()
        self.local_path.delete()
