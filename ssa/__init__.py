#!/usr/bin/env python
import pdb

#==============================================================================
# Common Functionality
#==============================================================================
from ssa.common import *
import ssa.java
import ssa.globals as g

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

parser.add_argument('--interactive',
        action="store_true",
        help="prompts for input before exiting." )

parser.add_argument('-c', '--count',
        action="store_true",
        help="count the lines of code in each file." )

parser.add_argument('--sql',
        action="store_true",
        help="print anything that looks like an SQL statement, and print !!SQLI!! when possible SQLi is detected." )

parser.add_argument('--sqli',
        action="store_true",
        help="print only possible SQLi, not the SQL statements" )

parser.add_argument('--syntax',
        action="store_true",
        help="print the syntax tree of each parsed Java source file" )

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
    paths = listify(g.args.args)
    # if no paths were specified, then switch to interactive mode and
    # prompt the user for paths.
    if len(paths) <= 0:
        g.args.interactive = True
        while True:
            line = raw_input('Enter source code path or file pattern.  To finish, enter a blank line: ').strip()
            if len(line) <= 0:
                break
            paths.append(line)
    # if no paths are specified, search the cwd.
    if len(paths) <= 0:
        print 'No paths specified, searching current dir: %s' % os.getcwd()
        paths.append('.')
    files = list(find_files(paths, patterns=g.args.pattern, ignore_patterns=g.args.ignore_pattern))
    return files

def run():
    if g.args.count: g.args.mode = 'count'
    elif g.args.sql: g.args.mode = 'sql'
    elif g.args.sqli: g.args.mode = 'sqli'
    elif g.args.syntax: g.args.mode = 'syntax'
    else: g.args.mode = 'sqli'
    g.args.pattern = listify(g.args.pattern)
    # if we're not counting lines, then we're scanning Java code.
    if g.args.mode != 'count':
        g.args.pattern += ['*.java']
    if isverbose():
        print 'Searching for files...'
    files = get_files()
    if g.args.mode == 'count':
        counter = LineCounter()
        counter.add(files)
        counter.count_lines()
    else:
        print 'Scanning %d java file(s)...' % len(files)
        ssa.java.scan(files)
    if g.args.interactive:
        wait_any_key()

def main():
    g.args, leftovers = parser.parse_known_args()
    g.args.args = leftovers
    run()

if __name__ == "__main__":
    main()


