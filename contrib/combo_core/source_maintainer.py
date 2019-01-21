from .source_locator import *


class JsonSourceMaintainer(JsonSourceLocator):
    def __init__(self, json_path):
        super(JsonSourceMaintainer, self).__init__(json_path)

    def add_project(self, project_name, source_type=None):
        if project_name in self._projects:
            requested_src_type = source_type or JsonSourceHandler.DEFAULT_SRC_TYPE
            actual_src_type = self._get_src_type(self._projects[project_name])
            assert requested_src_type == actual_src_type, 'Project already exists with different source type'
            return

        # Project does not exist, we need to add its details

        project_details = dict()

        # If the source type is not the default, we need to manually specify it
        if source_type is not None and source_type != JsonSourceHandler.DEFAULT_SRC_TYPE:
            project_details[JsonSourceHandler.IDENTIFIER_TYPE_KEYWORD] = source_type

        self._projects[project_name] = project_details

    def add_version(self, project_name, project_version, version_details):
        if project_name not in self._projects:
            raise UndefinedProject('Project {} could not be found'.format(project_name))

        project_details = self._projects[project_name]

        # This function is only relevant for version dependency source types
        source_type = project_details.get(JsonSourceHandler.IDENTIFIER_TYPE_KEYWORD, JsonSourceHandler.DEFAULT_SRC_TYPE)
        assert source_type == 'version_dependent', 'Unsupported action'

        # Remove details which are not necessary due to defaults
        project_defaults = project_details.get(VersionDependentSourceSupplier.SOURCE_DEFAULTS_KEYWORD)
        if project_defaults is not None:
            version_details = VersionDependentSourceSupplier.filter_version_details(version_details, project_defaults)

        project_details[str(project_version)] = version_details

        # This update is necessary for the file update
        self._projects[project_name] = project_details

