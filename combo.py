import combo_core.compat
from dependencies_manager import *

import argparse


def main():
    parser = argparse.ArgumentParser(description='Combo arguments')
    parser.add_argument('path', help='The path of the resolve repository')
    parser.add_argument('sources_json', help='An optional local sources json file instead of using the server',
                        nargs='?', default=None)
    args = parser.parse_args()

    DependenciesManager(Directory(args.path), args.sources_json).resolve()


if __name__ == '__main__':
    main()
