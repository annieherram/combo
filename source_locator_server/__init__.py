from .source_locator import *


sources_json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sources.json')
source_locator = SourceLocator(sources_json_path)


def get_version_source(project_name, version):
    """ Should be an independent server, currently a function instead """
    return source_locator.get_source(project_name, version)
