import sys
import platform

python_version = sys.version_info

if python_version.major == 2 and python_version.minor >= 7:
    string_types = (basestring, )
elif python_version.major == 3:
    string_types = (str, )
else:
    raise Exception('Unsupported python version detected: {}'.format(platform.python_version()))
