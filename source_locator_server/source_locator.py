import json
from .git_tags_locator import *


class UndefinedProject(BaseException):
    pass


class SpecificVersionHandler:
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
        self._specific_versions_dict = project_details

    def get_source(self, version_str):
        if version_str not in self._specific_versions_dict:
            raise RequestedVersionNotFound('Version {} could not be found for project {}'.format(
                version_str, self._project_name))

        specific_version_details = self._specific_versions_dict[version_str]
        try:
            specific_version_handler = SpecificVersionHandler(specific_version_details)
        except KeyError:
            raise KeyError('Version {} of project "{}" - keyword {} does not exist'.format(
                version_str, self._project_name, SpecificVersionHandler.TYPE_KEYWORD))

        source = specific_version_handler.get_source()
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
            raise UndefinedProject('Project {} is missing required attribute "{}"'.format(
                project_name, self.IDENTIFIER_TYPE_KEYWORD))

        project_src_type = project_details[self.IDENTIFIER_TYPE_KEYWORD]

        if project_src_type == 'version_dependent':
            source_supplier_type = VersionDependentSourceSupplier
        elif project_src_type == 'git_tags':
            source_supplier_type = GitTagsSourceSupplier
        else:
            raise KeyError('Unsupported {} value - {}'.format(self.IDENTIFIER_TYPE_KEYWORD, project_src_type))

        source_supplier = source_supplier_type(project_name, project_details)
        source = source_supplier.get_source(str(version))
        return source
