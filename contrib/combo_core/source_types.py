from combo_core import *
from .source_locator import *

'''
    Interfaces
'''


class DependencyBase(object):
    def __init__(self, dependency_source):
        self.dep_src = dependency_source

    def assert_keywords(self, *keywords):
        for keyword in keywords:
            assert keyword in self.dep_src, 'Invalid import source, missing attribute "{}"'.format(keyword)

    def clone(self, dst_path):
        raise NotImplementedError()


class DetailsProviderBase(object):
    def __init__(self, working_dir):
        self._working_dir = working_dir

    def _get_initial_dict(self):
        return {SpecificVersionHandler.TYPE_KEYWORD: self.get_type()}

    def get_type(self):
        raise NotImplementedError()

    def get_details(self):
        raise NotImplementedError()


'''
    Implementations
'''

# Git


class GitDetailsKeywords(object):
    TYPE_NAME = 'git'

    remote_url_keyword = 'remote_url'
    commit_hash_keyword = 'commit_hash'

    required_keywords = (remote_url_keyword, commit_hash_keyword)


class GitDependency(DependencyBase, GitDetailsKeywords):
    def clone(self, dst_path):
        from combo_core import git_api

        self.assert_keywords(*self.required_keywords)

        # Clone the dependency
        repo = git_api.GitRepo(dst_path)

        try:
            repo.clone(self.dep_src[self.remote_url_keyword], self.dep_src[self.commit_hash_keyword])
        except BaseException as e:
            # If there is an error, make sure the repo is still closed at the end
            repo.close()
            raise e

        repo.close()


class GitDetailsProvider(DetailsProviderBase, GitDetailsKeywords):
    def get_type(self):
        return self.TYPE_NAME

    def get_details(self):
        from combo_core import git_api

        repo = git_api.GitRepo(self._working_dir)

        details = self._get_initial_dict()
        details.update(repo.details())

        return details


# File System

class NonExistingPath(ComboException):
    pass


class FileSystemDependency(DependencyBase):
    PATH_KEYWORD = 'path'

    def clone(self, dst_path):
        self.assert_keywords(self.PATH_KEYWORD)

        src_path = Directory(self.dep_src[self.PATH_KEYWORD])
        if not src_path.exists():
            raise NonExistingPath('Local path {} does not exist'.format(src_path))

        Directory(src_path).copy_to(dst_path)


class FileSystemDetailsProvider(DetailsProviderBase):
    TYPE_NAME = 'file_system'
    PATH_KEYWORD = 'path'

    def get_type(self):
        return self.TYPE_NAME

    def get_details(self):
        details = self._get_initial_dict()
        details[self.PATH_KEYWORD] = self._working_dir.abs()
