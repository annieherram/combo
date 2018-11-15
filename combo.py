from __future__ import print_function

import combo_core.compat
import argparse
from dependencies_manager import *


class ComboCommands(object):
    def __init__(self):
        self._main_parser = argparse.ArgumentParser(description='Combo dependencies manager')

        self.add_subparsers()
        self._args = self._main_parser.parse_args()

        self._args.command()
        print('Done')

    def add_subparsers(self):
        subparsers = self._main_parser.add_subparsers()

        def add_manager_subparser_arguments(subparser):
            subparser.add_argument('--sources-json', '-j',
                                   help='An optional local sources json file instead of using the server',
                                   nargs='?', default=None)
            subparser.add_argument('--path', '-p', help='The path of the resolve repository',
                                   nargs='?', default=None)

        # Resolve
        resolve_parser = subparsers.add_parser('resolve')
        add_manager_subparser_arguments(resolve_parser)
        resolve_parser.set_defaults(command=self.resolve)

        # Is dirty
        is_dirty_parser = subparsers.add_parser('is-dirty')
        add_manager_subparser_arguments(is_dirty_parser)
        is_dirty_parser.set_defaults(command=self.is_dirty)

        # Check for updates
        check_for_updates_parser = subparsers.add_parser('check-for-updates')
        check_for_updates_parser.set_defaults(command=self.check_for_updates)

        # Check for updates
        delete_cache_parser = subparsers.add_parser('delete-cache')
        delete_cache_parser.set_defaults(command=self.delete_cache)

    def get_dependencies_manager(self):
        work_dir = Directory(self._args.path or os.path.curdir)

        if self._args.path is None:
            print('Working directory is', work_dir)

        if self._args.sources_json is None:
            print('Sources json was not specified. Combo server will be contacted for sources')

        return DependenciesManager(work_dir, self._args.sources_json)

    def resolve(self):
        manager = self.get_dependencies_manager()

        print('----------------------------------------------------------------------------------')
        print('Resolving')
        manager.resolve()
        manager.cleanup()
        print('----------------------------------------------------------------------------------')

    def is_dirty(self):
        manager = self.get_dependencies_manager()

        print('----------------------------------------------------------------------------------')
        print('Checking if the repository is dirty')
        manager.is_dirty(verbose=True)
        manager.cleanup()
        print('----------------------------------------------------------------------------------')

    def check_for_updates(self):
        print('Checking for updates')
        print('No implemented yet')

    def delete_cache(self):
        print('Deleting cached AppData')
        print('No implemented yet')


if __name__ == '__main__':
    ComboCommands()
