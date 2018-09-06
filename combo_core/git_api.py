import git
import gc
import os
import utils


class GitRepo:
    def __init__(self, local_path):
        self.local_path = local_path
        self._git_dir = os.path.join(local_path, '.git')

        self._repo = None
        self._tags = None

    def metadata_exists(self):
        return os.path.exists(self._git_dir)

    def empty(self):
        if not os.path.exists(self.local_path):
            return True
        return len(os.listdir(self.local_path)) == 0

    def clone(self, remote_url, ref=None):
        if not self.empty():
            raise EnvironmentError()

        if not os.path.exists(self.local_path):
            os.makedirs(self.local_path)

        self._repo = git.Repo.clone_from(remote_url, self.local_path)

        if ref:
            self.checkout(ref)

    def checkout(self, ref):
        self._repo.head.reference = ref
        self._repo.head.reset(working_tree=True)

    def tags(self):
        self._tags = self._repo.tags
        return self._tags

    def close(self):
        del self._tags, self._repo
        gc.collect()

        if self.metadata_exists():
            utils.rmtree(self._git_dir)

    def delete(self):
        self.close()
        utils.rmtree(self.local_path)
