# such-static-analysis
Source code scanner.  Scan a Java codebase for instances of SQL injection, or print out how many lines of code are in each file.

## Installation

### Windows

Download an installer from the
[Releases](//github.com/strayptr/such-static-analysis/releases) page.

### Unix, OS X, etc

```sh
pip install -r requirements.txt
```

setup.py hasn't been written yet.  For now, operate out of this
directory.

## Usage

```sh
# count how many lines of C code your project has.
ssascan path/to/your/c/src '*.c' '*.h' --count

# count how many lines of Python code your project has.
ssascan path/to/your/py/src '*.py' --count

# scan your Java project for instances of SQLi vulns.
ssascan path/to/your/java/src
```




