from combo_core import *
import json
import copy


class UndefinedProject(ComboException):
    pass


class UndefinedProjectVersion(ComboException):
    pass


class InvalidVersionDetails(ComboException):
    pass


class ProjectSource:
    def __init__(self, src_type, **kwargs):
        self.src_type = src_type

        if src_type == 'git':
            self.remote_url = kwargs['url']
            self.commit_hash = kwargs['commit_hash']
        elif src_type == 'local_path':
            self.local_path = kwargs['path']
        else:
            raise TypeError('Source type {} is not supported yet'.format(src_type))

    def __str__(self):
        return json.dumps(self.as_dict())

    def as_dict(self):
        return vars(self)


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
    SOURCE_DEFAULTS_KEYWORD = 'defaults'

    def __init__(self, project_name, project_details):
        self._project_name = project_name

        self._project_defaults = project_details[self.SOURCE_DEFAULTS_KEYWORD] \
            if self.SOURCE_DEFAULTS_KEYWORD in project_details else dict()

        self._specific_versions_dict = project_details

    def _get_version_details(self, version_dict):
        if SpecificVersionHandler.TYPE_KEYWORD in version_dict:
            # If we have a different type, the default is not relevant
            return version_dict

        # Update variables from the version dictionary into the default variables dictionary
        version_details = copy.deepcopy(self._project_defaults)
        version_details.update(version_dict)
        return version_details

    @staticmethod
    def filter_version_details(version_details, project_defaults):
        if SpecificVersionHandler.TYPE_KEYWORD not in version_details:
            raise InvalidVersionDetails('Missing attribute "{}"'.format(SpecificVersionHandler.TYPE_KEYWORD))

        # We want to filter details only if there is no default type, or the default type is ours
        if SpecificVersionHandler.TYPE_KEYWORD not in project_defaults:
            return
        if version_details[SpecificVersionHandler.TYPE_KEYWORD] != \
                project_defaults[SpecificVersionHandler.TYPE_KEYWORD]:
            return

        # The version details has the same type as the project defaults, we can filter
        # Take each record that either does not exist in the defaults, or exist with a different value
        filtered = {key: val for key, val in version_details.items()
                    if key not in project_defaults or project_defaults[key] != val}
        return filtered

    def get_source(self, version_str):
        if version_str not in self._specific_versions_dict:
            raise UndefinedProjectVersion('Version {} could not be found for project {}'.format(
                version_str, self._project_name))

        specific_version_details = self._get_version_details(self._specific_versions_dict[version_str])
        try:
            specific_version_handler = SpecificVersionHandler(specific_version_details)
        except KeyError:
            raise KeyError('Version {} of project "{}" - keyword "{}" does not exist'.format(
                version_str, self._project_name, SpecificVersionHandler.TYPE_KEYWORD))

        source = specific_version_handler.get_source()
        return source


class SourceLocator(object):
    def get_source(self, project_name, version):
        raise NotImplementedError()


class JsonSourceHandler:
    IDENTIFIER_TYPE_KEYWORD = 'general_type'
    DEFAULT_SRC_TYPE = 'version_dependent'

    def __init__(self, json_path):
        self._projects = JsonFile(json_path)

        self._supported_src_suppliers = {
            'version_dependent': VersionDependentSourceSupplier
        }

        if self.DEFAULT_SRC_TYPE not in self._supported_src_suppliers:
            raise UnhandledComboException('Invalid default source type {}'.format(self.DEFAULT_SRC_TYPE))

    def _get_src_type(self, project_details):
        if self.IDENTIFIER_TYPE_KEYWORD in project_details:
            return project_details[self.IDENTIFIER_TYPE_KEYWORD]
        return self.DEFAULT_SRC_TYPE

    def get_json_file_path(self):
        return str(self._projects)


class JsonSourceLocator(JsonSourceHandler, SourceLocator):
    def __init__(self, json_path):
        super(JsonSourceLocator, self).__init__(json_path)

    def project_exists(self, project_name):
        return project_name in self._projects

    def get_source(self, project_name, version):
        if project_name not in self._projects:
            raise UndefinedProject('Project {} could not be found'.format(project_name))

        project_details = self._projects[project_name]

        project_src_type = self._get_src_type(project_details)
        if project_src_type not in self._supported_src_suppliers:
            raise KeyError('Unsupported {} value - {}'.format(self.IDENTIFIER_TYPE_KEYWORD, project_src_type))

        source_supplier_type = self._supported_src_suppliers[project_src_type]
        source_supplier = source_supplier_type(project_name, project_details)
        source = source_supplier.get_source(str(version))
        return source.as_dict()
