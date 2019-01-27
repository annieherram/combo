from combo_core import *
import git
import gc
import os


class ReferenceNotFound(ComboException):
    pass


class GitRepo:
    def __init__(self, local_path):
        self.local_path = local_path
        self._git_dir = self.local_path.join('.git')

        self._repo = None
        self._tags = None

    def empty(self):
        if not self.local_path.exists():
            return True
        return len(os.listdir(self.local_path.path)) == 0

    def clone(self, remote_url, ref=None):
        if not self.empty():
            raise EnvironmentError()

        if not self.local_path.exists():
            os.makedirs(self.local_path.path)

        # TODO: Add timeout. Fix 'local_projects.json' file in case of timeout before exiting
        self._repo = git.Repo.clone_from(remote_url, self.local_path.path)

        if ref:
            self.checkout(ref)

    def remote_url(self, remote_name, push_url=False):
        # TODO: Extract URL from repository
        assert not self.empty() and remote_name == 'origin' and push_url is False
        return 'https://github.com/annieherram/combo_core.git'

    def commit_hash(self):
        # TODO: Run git status and check for the commit hash
        assert not self.empty()
        return 'thisisnotarealcommithashbutthelengthreal'

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
