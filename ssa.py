#!/usr/bin/env python
import pdb

#==============================================================================
# Common Functionality
#==============================================================================

#
# see http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
#
import os, fnmatch
def find_files(directory, patterns, ignore_patterns):
    patterns = patterns or ['*']
    if isinstance(patterns, str) or isinstance(patterns, unicode):
        patterns = [patterns]
    ignore_patterns = ignore_patterns or []
    if isinstance(ignore_patterns, str) or isinstance(ignore_patterns, unicode):
        ignore_patterns = [ignore_patterns]
    for root, dirs, files in os.walk(directory):
        for basename in files:
            for pattern in patterns:
                if fnmatch.fnmatch(basename, pattern):
                    ignored = False
                    for ignore_pattern in ignore_patterns:
                        if fnmatch.fnmatch(basename, ignore_pattern):
                            ignored = True
                            break
                    if not ignored:
                        filename = os.path.join(root, basename)
                        yield filename
                        break

#==============================================================================
# Cmdline
#==============================================================================
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, 
    description="""
TODO
""")

parser.add_argument('-v', '--verbose',
        action="store_true",
        help="verbose output" )

parser.add_argument('-p', '--pattern',
        action='append',
        help="file patterns of the files to count." )

parser.add_argument('-i', '--ignore-pattern',
        action='append',
        help="file patterns to skip." )

parser.add_argument('-c', '--count',
        action="store_true",
        help="count the lines of code in each file." )

parser.add_argument('--interactive',
        action="store_true",
        help="prompts for input before exiting." )

args = None

#==============================================================================
# Main
#==============================================================================
import sys
import os

class Path(object):
    def __init__(self, path):
        assert(isinstance(path, str) or isinstance(path, unicode))
        self._path = path

    @property
    def path(self):
        val = self._path
        val = os.path.normpath(val)
        val = os.path.normcase(val)
        return val

    @property
    def abspath(self):
        return os.path.abspath(self.path)

    @property
    def isfile(self):
        return os.path.isfile(self.path)

    @property
    def isdir(self):
        return os.path.isdir(self.path)

    @property
    def exists(self):
        return os.path.exists(self.path)

    def __eq__(self, other):
        if not isinstance(other, Path):
            other = Path(other)
        return self.abspath == other.abspath

    def __hash__(self):
        return hash(self.abspath)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '"%s"' % self.path


class FileSet(object):
    def __init__(self):
        self.added = set()
        self.files = []

    def add_file(self, filepath):
        path = Path(filepath)
        if not path.exists:
            print "Path doesn't exist: %s" % path
            return
        if not path.isfile:
            print "Path isn't a file: %s" % path
            return
        # if it was already added, ignore it.
        if path in self.added:
            return
        self.added.add(path)
        self.files.append(path)

class LineCounter(FileSet):
    def __init__(self):
        super(LineCounter, self).__init__()

    def linecounts(self):
        counted = set()
        for path in self.files:
            with open(path.abspath, 'r') as f:
                n = 0
                for line in f:
                    line = line.strip()
                    # ignore blank lines.
                    if len(line) <= 0:
                        continue
                    # ignore comments.  TODO: ignore block comments?
                    if line.startswith('//'):
                        continue
                    # count the line.
                    n += 1
                assert(path not in counted)
                counted.add(path)
                yield path, n
    
    def count_lines(self):
        lines = 0
        files = 0
        for filename, linecount in self.linecounts():
            print '%10d' % linecount, filename
            files += 1
            lines += linecount
        print '%d lines in %d files' % (lines, files)

def count_lines():
    counter = LineCounter()
    # for each arg on cmdline...
    patterns = args.pattern or list()
    ignore_patterns = args.ignore_pattern or list()
    paths = []
    for arg in args.args:
        # if the arg is a pattern, then add it to the list of
        # patterns.
        if arg.find('*') >= 0:
            patterns.append(arg)
            continue
        # otherwise it's a path.
        paths.append(arg)
    interactive = args.interactive
    # if no paths were specified, then switch to interactive mode and
    # prompt the user for paths.
    if len(paths) <= 0:
        interactive = True
        while True:
            line = raw_input('Enter source code path or file pattern.  To finish, enter a blank line: ')
            path_or_pattern = line.strip()
            if len(path_or_pattern) <= 0:
                break
            if path_or_pattern.find('*') >= 0:
                patterns.append(path_or_pattern)
            elif not os.path.exists(path_or_pattern):
                sys.stderr.write("Path doesn't exist: %s\n" % path_or_pattern)
            else:
                paths.append(path_or_pattern)
    # if no paths are specified, search the cwd.
    if len(paths) <= 0:
        print 'No paths specified, searching CWD: %s' % os.getcwd()
        paths.append('.')
    # search for files in each path.
    for path in paths:
        if not os.path.isdir(path):
            print 'Not a directory: %s' % path
            continue
        for filepath in find_files(path, patterns=patterns, ignore_patterns=ignore_patterns):
            counter.add_file(filepath)
    counter.count_lines()
    if interactive:
        wait_any_key()

import platform
def iswindows():
    return platform.system().lower().find('windows') >= 0

def wait_any_key():
    if iswindows():
        print "Press any key to continue..."
        import msvcrt as m
        return m.getch()
    else:
        return raw_input("Press enter to continue...")
        
def run():
    count_lines()

def main():
    global args
    args, leftovers = parser.parse_known_args()
    args.args = leftovers
    run()

if __name__ == "__main__":
    main()

