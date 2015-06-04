#!/usr/bin/env python
import pdb

#==============================================================================
# Common Functionality
#==============================================================================
from ssa.common import *
import ssa.java

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


def get_files():
    paths = listify(args.args)
    # if no paths were specified, then switch to interactive mode and
    # prompt the user for paths.
    if len(paths) <= 0:
        args.interactive = True
        while True:
            line = raw_input('Enter source code path or file pattern.  To finish, enter a blank line: ').strip()
            if len(line) <= 0:
                break
            paths.append(line)
    # if no paths are specified, search the cwd.
    if len(paths) <= 0:
        print 'No paths specified, searching current dir: %s' % os.getcwd()
        paths.append('.')
    files = list(find_files(paths, patterns=args.pattern, ignore_patterns=args.ignore_pattern, verbose=True))
    return files

def run():
    if not args.count:
        # if we're not counting lines, then we're scanning Java code.
        args.pattern = listify(args.pattern)
        args.pattern += ['*.java']
    print 'Searching for files...'
    files = get_files()
    if args.count:
        counter = LineCounter()
        counter.add(files)
        counter.count_lines()
    else:
        print 'Scanning %d java file(s)...' % len(files)
        ssa.java.scan(files)
    if args.interactive:
        wait_any_key()

def main():
    global args
    args, leftovers = parser.parse_known_args()
    args.args = leftovers
    run()

if __name__ == "__main__":
    main()


