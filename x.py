from semantic_version import *


def m(*versions):
    x = '^' + str(min(versions))
    return all(Spec(x).match(ver) for ver in versions)


print m(Version('1.1.0'), Version('1.3.0'), Version('1.2.5'))

print m(Version('2.1.0'), Version('1.3.0'), Version('1.2.5'))

print m(Version('0.1.0'), Version('0.1.1'), Version('0.1.2'))
