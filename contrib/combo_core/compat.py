from os import path, environ
import sys
import platform

APP_NAME = "Combo"

python_version = sys.version_info

if python_version.major == 2 and python_version.minor >= 7:
    import socket
    string_types = (basestring, )
    connection_error = socket.error
elif python_version.major == 3:
    string_types = (str, )
    connection_error = ConnectionError
else:
    raise EnvironmentError('Unsupported python version detected: {}'.format(platform.python_version()))


if sys.platform == 'win32':
    appdata_dir_path = path.join(environ['APPDATA'], APP_NAME)
elif sys.platform.startswith('linux'):
    appdata_dir_path = path.expanduser(path.join("~", "." + APP_NAME))
else:
    raise EnvironmentError('Unsupported platform detected: {}'.format(sys.platform))
