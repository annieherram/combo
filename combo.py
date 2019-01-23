from __future__ import print_function

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'contrib')))

import combo_core.compat
import argparse
from dependencies_manager import *
from settings import COMBO_SERVER_ADDRESS


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
            subparser.add_argument('--path', '-p', help='The path of the repository', nargs='?', default=None)
            subparser.add_argument('--force', '-f', action="store_true", help='Ignore corrupted dependencies')

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

        # Delete cache
        delete_cache_parser = subparsers.add_parser('delete-cache')
        delete_cache_parser.set_defaults(command=self.delete_cache)

        # Clear old outputs
        clear_old_outputs_parser = subparsers.add_parser('clear-old-outputs')
        clear_old_outputs_parser.add_argument('old_outputs_dir', metavar='old-outputs-dir',
                                              help='Previous directory for dependency outputs')
        clear_old_outputs_parser.set_defaults(command=self.clear_old_outputs)

        # Upload
        upload_parser = subparsers.add_parser('upload')
        upload_parser.add_argument('--path', '-p', help='The path of the repository', nargs='?', default=None)
        upload_parser.set_defaults(command=self.upload)

    def get_sources_locator(self, server_required=False):
        if not server_required:
            if self._args.sources_json is not None:
                return JsonSourceLocator(self._args.sources_json)

            print('Sources json was not specified. Combo server will be contacted for sources')

        return ServerSourceMaintainer(COMBO_SERVER_ADDRESS)

    def get_working_dir(self):
        work_dir = Directory(self._args.path or os.path.curdir)

        if self._args.path is None:
            print('Working directory is', work_dir)

        return work_dir

    def get_dependencies_manager(self):
        work_dir = self.get_working_dir()
        sources_locator = self.get_sources_locator()
        return DependenciesManager(work_dir, sources_locator)

    def resolve(self):
        manager = self.get_dependencies_manager()

        print('----------------------------------------------------------------------------------')
        print('Resolving')
        manager.resolve(self._args.force)
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

    def clear_old_outputs(self):
        print('Clearing dependencies from the old output directory')
        old_outputs_dir = Directory(self._args.old_outputs_dir)
        cleared = False

        # Clear only paths that are combo repositories
        for subdir in old_outputs_dir.sons():
            if Manifest.is_combo_repo(subdir):
                subdir.delete()
                cleared = True

        if not cleared:
            print('Nothing to clear')

    def upload(self):
        print('Uploading current version to the server')
        source_maintainer = self.get_sources_locator(server_required=True)
        manifest = Manifest(self.get_working_dir())

        # TODO: Use git commands to get the actual details
        version_details = {'type': 'git', 'url': 'thisistheurl', 'commit_hash': 'thisisthecommithash'}

        source_maintainer.add_version(manifest.name, manifest.version, version_details)


if __name__ == '__main__':
    ComboCommands()
