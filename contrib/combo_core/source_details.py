from .importer import *


class SourceDetailsProvider:
    def __init__(self, working_dir):
        self._handlers = {
            GitDetailsProvider.TYPE_NAME: GitDetailsProvider,
            LocalPathDetailsProvider.TYPE_NAME: LocalPathDetailsProvider
        }

        self._working_dir = working_dir

    def get_details(self, source_type):
        provider = self._handlers[source_type](self._working_dir)
        return provider.get_details()


class DetailsProviderBase(object):
    def __init__(self, working_dir):
        self._working_dir = working_dir

    def _get_initial_dict(self):
        return {SpecificVersionHandler.TYPE_KEYWORD: self.get_type()}

    def get_type(self):
        raise NotImplementedError()

    def get_details(self):
        raise NotImplementedError()


class LocalPathDetailsProvider(DetailsProviderBase):
    TYPE_NAME = 'local_path'
    PATH_KEYWORD = 'local_path'

    def get_type(self):
        return self.TYPE_NAME

    def get_details(self):
        details = self._get_initial_dict()
        details[self.PATH_KEYWORD] = self._working_dir.abs()


class GitDetailsProvider(DetailsProviderBase, GitDetailsKeywords):
    def get_type(self):
        return self.TYPE_NAME

    def get_details(self):
        from combo_core import git_api

        repo = git_api.GitRepo(self._working_dir)

        details = self._get_initial_dict()
        details.update(repo.details())

        return details
