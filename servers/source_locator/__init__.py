import json
from utils import *


class ProjectSource:
    def __init__(self, src_type, **kwargs):
        self.src_type = src_type

        if src_type == 'git':
            self.remote_url = kwargs['url']
            self.commit_hash = kwargs['commit_hash']
        else:
            raise TypeError('Source type {} is not supported yet'.format(src_type))


class MajorVersionMismatch(BaseException):
    pass


class RequestedVersionNotFound(BaseException):
    pass


class UndefinedProject(BaseException):
    pass


class VersionFormatter:
    def __init__(self, prefix_format=''):
        self._prefix = prefix_format

    def get_as_tuple(self, version_str):
        assert version_str.startswith(self._prefix), \
            'Version string is expected to start with the prefix "{}"'.format(version_str)
        return tuple(map(int, version_str[len(self._prefix):].split(".")))

    def get_latest(self, version_strings):
        tuples = map(self.get_as_tuple, version_strings)
        max_version = max(tuples)

        # If there is a dependency with a different major number, raise an error
        # TODO: Remove comment
        # if any(version[0] < max_version[0] for version in tuples):
        #     raise MajorVersionMismatch

        return filter(lambda v: self.get_as_tuple(v) == max_version, version_strings)[0]


class GitTagsVersionFormatter(VersionFormatter):
    def __init__(self, prefix_format):
        VersionFormatter.__init__(self, prefix_format)

    def is_version(self, tag):
        try:
            self.get_as_tuple(str(tag))
        except (AssertionError, ValueError):
            return False
        return True

    def get_version_tags(self, tags):
        return filter(self.is_version, tags)

    def get_requested_version(self, tags, requested_version_tuple):
        version_tags = self.get_version_tags(tags)
        try:
            return xfilter(lambda tag: self.get_as_tuple(str(tag)) == requested_version_tuple, version_tags)
        except ObjectNotFound as e:
            raise RequestedVersionNotFound(e)

    def get_latest_from_tags(self, tags):
        version_tags = self.get_version_tags(tags)
        max_version = max(map(self.get_as_tuple, map(str, version_tags)))
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == max_version, version_tags)


class GitTagsSourceSupplier:
    def __init__(self, project_name, project_details):
        self._project_name = project_name
        self._remote_url = project_details['url']
        self._tags_prefix = project_details.get('tags_prefix') or ''

    def get_source(self, version_str):
        commit_hash = self._search_tags(version_str)
        source = ProjectSource('git', url=self._remote_url, commit_hash=commit_hash)
        return source

    def _search_tags(self, version_str):
        import git

        working_dir = os.path.dirname(os.path.realpath(__file__))
        dst_path = os.path.join(working_dir, self._project_name).lower().replace(' ', '_')

        repo = git.Repo.clone_from(self._remote_url, dst_path)

        requested_version_tuple = VersionFormatter().get_as_tuple(version_str)
        selected_tag = GitTagsVersionFormatter(self._tags_prefix).\
            get_requested_version(repo.tags, requested_version_tuple)

        # The commit hash has to be stored now, because after folder deletion there is no way to get it
        commit_hash = str(selected_tag.commit)

        del selected_tag, repo
        rmtree(dst_path)
        return commit_hash


class VersionHandler:
    TYPE_KEYWORD = 'type'

    def __init__(self, version_details):
        if self.TYPE_KEYWORD not in version_details:
            raise KeyError('Version details does not include keyword "{}"'.format(self.TYPE_KEYWORD))

        self._details = version_details
        self._src_type = version_details[self.TYPE_KEYWORD]

    def get_source(self):
        return ProjectSource(self._src_type, **self._details)


class VersionDependentSourceSupplier:
    def __init__(self, project_name, project_details):
        self._project_name = project_name
        self._versions_dict = project_details

    def get_source(self, version_str):
        if version_str not in self._versions_dict:
            raise RequestedVersionNotFound('Version {} could not be found for project {}'.format(
                version_str, self._project_name))

        version_details = self._versions_dict[version_str]
        try:
            version_handler = VersionHandler(version_details)
        except KeyError:
            raise KeyError('Version {} of project "{}" - keyword {} does not exist'.format(
                version_str, self._project_name, VersionHandler.TYPE_KEYWORD))

        source = version_handler.get_source()
        return source


class SourceLocator:
    IDENTIFIER_TYPE_KEYWORD = 'general_type'

    def __init__(self, json_path):
        with open(json_path, 'r') as json_file:
            self._projects = json.load(json_file)

    def get_source(self, project_name, version):
        if project_name not in self._projects:
            raise UndefinedProject('Project {} could not be found'.format(project_name))

        project_details = self._projects[project_name]

        if self.IDENTIFIER_TYPE_KEYWORD not in project_details:
            raise UndefinedProject('Project {} does not have required attribute "{}"'.format(
                project_name, self.IDENTIFIER_TYPE_KEYWORD))

        project_src_type = project_details[self.IDENTIFIER_TYPE_KEYWORD]

        if project_src_type == 'version_dependent':
            version_supplier_type = VersionDependentSourceSupplier
        elif project_src_type == 'git_tags':
            version_supplier_type = GitTagsSourceSupplier
        else:
            raise KeyError('Unsupported {} value - {}'.format(self.IDENTIFIER_TYPE_KEYWORD, project_src_type))

        version_supplier = version_supplier_type(project_name, project_details)
        source = version_supplier.get_source(version)
        return source


sources_json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sources.json')
source_locator = SourceLocator(sources_json_path)


def get_version_source(project_name, version):
    """ Should be an independent server, currently a function instead """
    return source_locator.get_source(project_name, version)
