import json
from utils import *

urls_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'projects.json')
with open(urls_path, 'r') as f:
    urls_json = json.load(f)


def project_name_to_url(project_name):
    # This should be a server with TCP requests instead
    if project_name not in urls_json:
        raise KeyError("Project {} not found".format(project_name))

    return urls_json[project_name]
