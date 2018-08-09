from dependencies_manager import *
import sys


def main():
    my_path = sys.argv[1]
    DependenciesManager(my_path).resolve()


if __name__ == '__main__':
    main()
