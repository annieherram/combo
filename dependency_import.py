"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from servers import *


class DependencyBase(object):
    def __init__(self, dependency_source):
        self.dep_src = dependency_source

    def clone(self, dst_path):
        raise NotImplementedError


class GitDependency(DependencyBase):
    REMOTE_URL_KEYWORD = 'remote_url'
    COMMIT_HASH_KEYWORD = 'commit_hash'

    def clone(self, dst_path):
        for keyword in (self.REMOTE_URL_KEYWORD, self.COMMIT_HASH_KEYWORD):
            assert hasattr(self.dep_src, keyword), 'Invalid import source, missing attribute "{}"'.format(keyword)

        import git

        # Clone the dependency
        repo = git.Repo.clone_from(getattr(self.dep_src, self.REMOTE_URL_KEYWORD), dst_path)

        # Checkout to the requested commit
        repo.head.reference = getattr(self.dep_src, self.COMMIT_HASH_KEYWORD)
        repo.head.reset(working_tree=True)

        rmtree(os.path.join(dst_path, '.git'))


class DependencyImporter:
    def __init__(self):
        self.handler_dict = {
            'git': GitDependency
        }

    def clone(self, project_name, version, dst_path):
        import_src = get_version_source(project_name, version)

        if import_src.src_type not in self.handler_dict:
            raise NotImplementedError('Can not import dependency with source type "{}"'.format(import_src.src_type))

        dependency_import_handler = self.handler_dict[import_src.src_type](import_src)
        dependency_import_handler.clone(dst_path)
