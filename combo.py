from dependencies_manager import *
from compat import *


def main():
    my_path = sys.argv[1]
    DependenciesManager(my_path).resolve()


if __name__ == '__main__':
    main()
