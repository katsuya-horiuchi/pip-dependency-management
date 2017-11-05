# -*- coding: utf-8 -*-

"""Simple standalone script to manage dependencies with pip

Author: Katsuya Horiuchi
Version: 1.0
License: Apache License 2.0

It is assumed that you're using pip and `requirements.txt` to manage
dependencies, and that `pip` can be called without specifying absolute path.

USAGE:
1. In the directory that contains `requirements.txt`, run the following command
   to generate `requirements.json` file;
       $ python dependencies.py --config
   If you use virtualenv to keep track of dependencies, run the command above
   from the virtualenv environment.

2. Use the following command to list packages that seemed to be installed by
   user;
       $ python dependencies.py --check

3. If you'd like to uninstall a certain package, run the following command
   to see if you can delete the packages and if you can delete other packages
   at the same time;
       $ python dependencies.py --delete PACKAGE_NAME

NOTE:
* You can create alias;
       $ alias pip_manage="python path/to/dependencies.py"
  By not specifying absolute path to Python, you can use the command from
  different virtualenv environments.
"""

from __future__ import print_function
import argparse
import copy
import json
import ntpath
import os
import re
from subprocess import Popen, PIPE
import sys

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda _: _  # Does nothing

REQUIREMENTS = os.path.join(os.getcwd(), 'requirements.txt')
CONFIG = os.path.join(os.getcwd(), 'requirements.json')
LINE_MATCH = re.compile(r'Requires:')
PKG_MATCH = re.compile(r'([A-Za-z0-9-_]+)(,|$)')
# Packages installed by default wouldn't show up in requirements.txt file.
DEFAULT_PKGS = ['setuptools', 'wheel']


def not_found(filename):
    """Throw an exception when a file wasn't found"""
    raise FileNotFoundError('Not found: `%s`' % ntpath.basename(filename))


class Config:

    def __init__(self):
        self.__get_data()

    def __get_data(self):
        with open(REQUIREMENTS, 'r') as fp:
            self.pkgs = [
                line.split('==')[0].lower() for line in fp.read().splitlines() \
                if len(line.split('==')) == 2 and \
                '#' not in line.split('==')[0]  # Escape comments, etc.
            ]
        self.data = {}
        print('Executing `pip show` for every package. '
              'This might take a while...')
        for pkg in tqdm(self.pkgs):
            dependencies = self.get_requirements(pkg)
            self.data[pkg] = dependencies
        return self

    @staticmethod
    def get_requirements(package):
        """Get dependencies of a given package"""
        process = Popen(['pip', 'show', '%s' % package],
                        stdout=PIPE,
                        stderr=PIPE)
        stdout, _ = process.communicate()
        lines = stdout.splitlines()
        for line in lines:
            if b'Requires:' not in line:  # Each line is byte-type
                continue
            matches = PKG_MATCH.findall(line.decode('utf-8'))
            if matches is not None:
                return [elem[0].lower() for elem in matches]

    def __recursive(self, dependencies):
        updated = False
        data = copy.deepcopy(dependencies)
        for elem in dependencies:
            # Default pkgs aren't show in requirements.txt
            if elem in DEFAULT_PKGS:
                continue

            result = self.data[elem]
            if result is not None:
                for item in result:
                    if item not in dependencies:
                        data.update(result)
                        updated = True
        return updated, data

    def create_config(self):
        """Create `requirements.json` file"""
        data = {}  # Dictionary saved as JSON file later
        for pkg in self.pkgs:
            dependencies = set(self.data[pkg])
            while True:
                updated, dependencies = self.__recursive(dependencies)
                if not updated:
                    data[pkg] = sorted(dependencies)
                    break
        with open(CONFIG, 'w') as fp:
            json.dump(data, fp, indent=4, separators=(',', ':'))
        print('%s was created.' % ntpath.basename(CONFIG))


class Delete:

    def __init__(self):
        self.data = self.__get_data()

    def __get_data(self):
        with open(CONFIG, 'r') as fp:
            return json.load(fp)

    def __get_parents(self, *args):
        parents_pkgs = set([])
        for pkg in args:
            for pkg_name, dependencies in self.data.items():
                if pkg in dependencies:
                    parents_pkgs.add(pkg_name)
        return parents_pkgs

    def __recursive(self, *args):
        updated = False
        deletables = list(args)  # Packages in `args` are already ok to uninstall
        dependencies = set([])
        for arg in list(args):
            if arg in DEFAULT_PKGS:
                continue
            dependencies.update(
                [p for p in self.data[arg] if p not in DEFAULT_PKGS]
            )
        for dependency in dependencies:
            parents = [d for d in self.__get_parents(dependency) if d not in args]
            if not parents:
                if dependency not in deletables:
                    deletables.append(dependency)
                    updated = True
        return updated, deletables

    def delete(self, pkg):
        """Check if given package can be uninstalled"""
        try:
            dependencies = [
                item for item in self.data[pkg] if item not in DEFAULT_PKGS
            ]
        except KeyError:
            sys.stderr.write(
                "Package `%s` isn't in %s. " % (pkg, ntpath.basename(CONFIG)) +
                'Make sure the file is up to date.\n'
            )
            sys.exit(1)
        parents = self.__get_parents(pkg)

        if dependencies:
            print("Dependencies of `%s`: %s" % \
                    (pkg, ', '.join(sorted(dependencies))))
        else:
            print("Package `%s` doesn't have any dependency." % pkg)
        if parents:
            print('Package `%s` is a denendency of these one(s): %s' % \
                  (pkg, ', '.join(sorted(parents))))
        else:
            print('No package has `%s` as dependency. ' % pkg +
                  "You can delete it if you'd like.")

        if not dependencies:
            sys.exit(0)    # No additional package is uninstallable
        deletable = set([])
        while True:
            updated, deletable = self.__recursive(*set([pkg, *deletable]))
            if not updated:
                break
        if not deletable:
            sys.exit(0)  # No additional package is uninstallable
        deletable = set(deletable)  # Remove duplicates
        deletable.remove(pkg)
        if deletable:
            print('Additionally, you can uninstall these packages: '
                  '%s' % ', '.join(sorted(deletable)))


def check():
    """Lists packages that are seemingly installed by user"""
    deletables = []
    with open(CONFIG, 'r') as fp:
        data = json.load(fp)
    for pkg in data.keys():
        count = 0
        for _, dependencies in data.items():
            if pkg in dependencies:
                count += 1
        if count == 0:
            deletables.append(pkg)
    print("Seems like you've installed these packages: "
          '%s' % ', '.join(sorted(deletables)))


def get_args():
    """Parse arguments from CLI"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        action='store_true',
        help='Create `requirements.json` file'
    )
    parser.add_argument(
        '--delete',
        type=str,
        help='Check if given package can be uninstalled'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='List all the packages that can be deleted'
             'without affecting any other packages'
    )
    if len(sys.argv) == 1:  # Show help if no argument was passed and exit
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    if args.config:
        assert os.path.exists(REQUIREMENTS), not_found(REQUIREMENTS)
        print('Creating `%s` file...' % ntpath.basename(CONFIG))
        Config().create_config()
    if args.delete is not None:
        assert os.path.exists(CONFIG), not_found(CONFIG)
        Delete().delete(args.delete.lower())
    if args.check:
        assert os.path.exists(CONFIG), not_found(CONFIG)
        check()


if __name__ == '__main__':
    main()
