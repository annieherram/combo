from __future__ import print_function
from utils import *
import git
from version2commit import *


class Combo:
    def __init__(self, repo_path, manifest, urls):
        self._repo_name = manifest['name']
        self._dependencies = dict((dep['name'], dep) for dep in manifest['dependencies'])
        self._output_dir = os.path.abspath(manifest['output_directory'])
        self._is_exec = bool(manifest['is_executable'])

        self._urls = urls
        self._my_repo = git.Repo(repo_path)

        self.validate_params()

    def validate_params(self):
        for dep in self._dependencies.values():
            assert dep['name'] in self._urls, "Count not find a source for dependency '{}'".format(dep['name'])

    def get_dependency_dir(self, dep):
        dep_name = dep if isinstance(dep, basestring) else dep['name']
        return os.path.join(self._output_dir, dep_name.lower().replace(' ', '_'))

    def apply(self):
        """ Commit the current manifest's into your repository """
        self.sync()

        for dep in self._dependencies:
            # Stage all files of the current dependency
            dep_dir = self.get_dependency_dir(dep)
            self._my_repo.index.add([dep_dir])

        # Commit the changes
        self._my_repo.index.commit('Manifest apply', parent_commits=[self._my_repo.commit()])

    def sync(self):
        """ Iterate the dependencies and clone them to the configured version """
        for dep_name, dep in self._dependencies.items():
            # Clone the dependency
            dst_path = self.get_dependency_dir(dep_name)
            repo_url = self._urls[dep_name]
            dep['repo'] = git.Repo.clone_from(repo_url, dst_path)

            # Checkout to the requested commit
            dep['commit_hash'] = version2commit(dep['repo'], dep_name, dep['version'])
            dep['repo'].head.reference = dep['commit_hash']

            rmtree(os.path.join(dst_path, ".git"))
