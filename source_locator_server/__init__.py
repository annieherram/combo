from .source_locator import *


def get_version_source(project_name, version, manual_sources_file=None):
    manual_source_locator = SourceLocator(manual_sources_file)
    return vars(manual_source_locator.get_source(project_name, version))
