from __future__ import print_function

import combo_core.compat
from dependencies_manager import *
import os

import argparse


def resolve(manager):
    print('Resolving')
    manager.resolve()


def is_dirty(manager):
    print('Checking if the repository is dirty')
    manager.is_dirty(verbose=True)


def check_for_updates(manager):
    print('Checking for updates')
    print('No implemented yet')
    print(manager)


def delete_cache(manager):
    print('Deleting cached AppData')
    print('No implemented yet')
    print(manager)


commands = {
    'resolve': resolve,
    'is_dirty': is_dirty,
    'check_for_updates': resolve,
    'delete_cache': resolve
}


def main():
    parser = argparse.ArgumentParser(description='Combo arguments')
    parser.add_argument('command', help='[{}]'.format(' / '.join(commands.keys())))
    parser.add_argument('--sources-json', '-j', help='An optional local sources json file instead of using the server',
                        nargs='?', default=None)
    parser.add_argument('--path', '-p', help='The path of the resolve repository', nargs='?', default=None)

    args = parser.parse_args()
    work_dir = Directory(args.path or os.path.curdir)

    if args.path is None:
        print('Working directory is', work_dir)

    if args.sources_json is None:
        print('Sources json was not specified. Combo server will be contacted for sources')

    dependencies_manager = DependenciesManager(work_dir, args.sources_json)

    print('----------------------------------------------------------------------------------')
    chosen_command = commands[args.command]
    chosen_command(dependencies_manager)

    dependencies_manager.cleanup()
    print('Done')
    print('----------------------------------------------------------------------------------')


if __name__ == '__main__':
    main()
