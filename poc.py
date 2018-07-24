from __future__ import print_function
from utils import *
import git
import sys
from version2commit import *


base_dir = os.path.join(os.path.curdir, "../")
repo_dir = os.path.abspath(os.path.join(base_dir, 'my_repo'))
if os.path.exists(repo_dir):
    rmtree(repo_dir)


# repo.create_tag("test")

# pygit2_url = "https://github.com/libgit2/pygit2.git"
# repo = git.Repo.clone_from(pygit2_url, repo_dir)
# repo = git.Repo(local_url)

# real_version = get_latest_version(repo.tags)
# fake_version = get_latest_version(["v2.9.1000", "v3.100.1"])
# print "The newest version is {}, commit {}".format(real_version, real_version.commit)
# print "master's commit hash is", repo.branches.master.commit

class Combo:
    def __init__(self, manifest, urls, verbose=False):
        self._repo_name = manifest['name']
        self._dependencies = manifest['dependencies']
        self._output_dir = manifest['output_directory']
        self._is_exec = bool(manifest['is_executable'])

        self._urls = urls
        self._verbose = verbose

    def foo(self, msg):
        if self._verbose:
            print(msg)

    def sync(self):
        self.foo('project {} (is_executable = {})'.format(self._repo_name, self._is_exec))

        for dep in self._dependencies:
            dep_name = dep['name']

            # Clone the dependency
            formatted_name = dep_name.lower().replace(' ', '_')
            dst_path = os.path.join(self._output_dir, formatted_name)
            repo_url = self._urls[dep_name]
            repo = git.Repo.clone_from(repo_url, dst_path)

            commit = version2commit(repo, dep_name, dep['version'])

            # Checkout
            repo.head.reference = commit

            branches = filter(lambda r: isinstance(r, git.RemoteReference), repo.refs)
            latest_version = get_latest_version(repo.tags, 'release_v')
            self.foo('latest version {} commit {}'.format(latest_version, latest_version.commit))
            self.foo('{} heads count -  {}:'.format(dep_name, len(repo.heads)) + str(repo.heads))
