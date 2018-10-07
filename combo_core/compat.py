from os import path, environ
import sys
import platform

APP_NAME = "Combo"

python_version = sys.version_info

if python_version.major == 2 and python_version.minor >= 7:
    string_types = (basestring, )
elif python_version.major == 3:
    string_types = (str, )
else:
    raise EnvironmentError('Unsupported python version detected: {}'.format(platform.python_version()))


if sys.platform == 'win32':
    appdata_dir = path.join(environ['APPDATA'], APP_NAME)
elif sys.platform.startswith('linux'):
    appdata_dir = path.expanduser(path.join("~", "." + APP_NAME))
else:
    raise EnvironmentError('Unsupported platform detected: {}'.format(sys.platform))
