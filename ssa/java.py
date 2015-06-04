from ssa.common import *
import pdb

VERBOSE=False

def scan(files):
    ctx = JavaContext()
    #
    # initial parsing.
    #
    files = listify(files)
    for i in xrange(len(files)):
        filepath = files[i]
        progress = '(%d/%d)' % (i, len(files))
        if g.args.mode == 'syntax':
            print '\n%s:' % filepath
        else:
            print '%s Parsing %s' % (progress, filepath)
        unit = ctx.add_file(filepath)
        if g.args.mode == 'syntax':
            print pp(unit.tree)
    if g.args.mode == 'syntax':
        return
    # 
    # SQL scanning.
    #
    sqlfinder = FindSQL(ctx)
    if g.args.mode == 'sqli':
        sqlfinder.find_sqli()
    else:
        asserting(not "unknown mode")

def parse_file(filename):
    parser = _startup()
    tree = parser.parse_file(filename)
    if tree:
        preprocessor = Preprocess(tree)
        processed = preprocessor.tree
        return processed

#==============================================================================
# Java-specific Functionality
#==============================================================================
import plyj.model as jmodel
import plyj.parser

g_parser = None

def _startup():
    global g_parser
    if not g_parser:
        g_parser = plyj.parser.Parser()
    return g_parser


class JavaContext(object):
    def __init__(self, files=[]):
        self.files = {}
        for filepath in files:
            self.add_file(filepath)

    def add_file(self, filepath):
        path = mkpath(filepath)
        if not path.isfile:
            print 'JavaContext: not a file: %s' % path
            return
        # parse the file.
        tree = parse_file(filepath)
        if tree:
            unit = JavaFile(self, filepath, tree)
            self.files[path] = unit
            return unit


    def get_file(self, filepath):
        return self.files[filepath]
    
    def each_file(self):
        return self.files.itervalues()


class JavaFile(object):
    def __init__(self, ctx, path, tree):
        self.ctx = ctx
        self._path = mkpath(path)
        self.tree = tree
        # load the file.
        #with open(self.path, 'r') as f:
            #self.src = f.read()
        # parse the file.
        self.scope = JavaScope(ctx, self, self.tree, parent=self)

    @property
    def path(self):
        return str(self._path)

    def __repr__(self):
        return 'JavaFile(%s)' % repr(self.path)


#
# A lexical scope is anything that can contain declarations or
# statements, e.g. a class, a method, etc.
#
class JavaScope(jmodel.Visitor):
    def __init__(self, ctx, unit, tree, parent=None):
        super(JavaScope, self).__init__(verbose=VERBOSE)
        asserting(tree)
        self.ctx = ctx
        self.tree = tree
        self.parent = parent
        self.decls = {}
        self.unit = unit
        # parse the scope.
        self.tree.accept(self)

    def resolve(self, name):
        pass

    def leave_FieldDeclaration(self, cur):
        for field in jFieldDecl(cur):
            self.add_field(field)

    def add_field(self, field):
        self.add_decl(field['name'], field)

    def add_decl(self, name, val):
        #asserting(name not in self.decls) # TODO: fix nested scopes.
        self.decls[name] = val

#==============================================================================
# plyj-Specific Functionality
#==============================================================================

#------------------------------------------------------------------------------
# pretty-print.
#------------------------------------------------------------------------------

def ind(count=0):
    return '    '*count

def ppjoin(sep, vals, indent):
    return ("%s\n%s" % (sep, ind(indent + 1))).join(vals)

def ppargs(vals, indent, p=False):
    if p:
        vals = [pp(x, indent) for x in vals]
    args = ppjoin(',', vals, indent)
    if len(vals) > 1:
        args = nl(indent) + args + nl(indent - 1)
    return args

def nl(indent):
    return ppjoin('', ['', ''], indent)
#
# pretty-print.
#
def pp(x, indent=0):
    if is_str(x):
        return repr(x)
    if is_iterable(x):
        vals = [val for val in x]
        if len(vals) <= 0:
            return '[]'
        elif len(vals) == 1:
            vals = [pp(val, indent=(indent)) for val in vals]
            return '[%s]' % (ppjoin(',', vals, indent))
        else:
            vals = [pp(val, indent=(indent + 1)) for val in vals]
            val = nl(indent)
            val += ppjoin(',', vals, indent)
            val += nl(indent)
            return '[%d|%s|%d]' % (len(vals), val, len(vals))
    if isname(x):
        return 'Name(%s)' % x.value
    if isliteral(x):
        return 'Literal(%s)' % x.value
    if isexpr(x):
        return 'Expression(%s)' % pp(x.expression, indent + 1)
    if isinstance(x, jmodel.MethodInvocation):
        method = x
        assert(len(method.type_arguments) == 0)
        result = '%s(%s)' % (method.name, ppargs(method.arguments, indent + 1, p=True))
        if method.target:
            if isname(method.target):
                target = jName(method.target)
            else:
                target = pp(method.target, indent + 1)
            result = '%s.%s' % (target, result)
        return result
    if isinstance(x, jmodel.SourceElement):
        elem = x
        equals = ("{0}={1}".format(k, pp(getattr(elem, k), indent=(indent + 1)))
                  for k in elem._fields)
        equals = list(equals)
        args = ppargs(equals, indent)
        return "{0}({1})".format(elem.__class__.__name__, args)
    return repr(x)

#------------------------------------------------------------------------------
# utilities for working with plyj.model objects.
#------------------------------------------------------------------------------

def jName(name):
    asserting(name)
    if is_str(name):
        return name
    asserting(hasattr(name, 'value'))
    asserting(is_str(name.value))
    return name.value

def jType(typ):
    if is_str(typ):
        return typ
    elif isinstance(typ, jmodel.Type):
        #asserting(len(typ.type_arguments) <= 0) # TODO: figure out what this is for.
        asserting(not typ.enclosed_in)
        name = jName(typ.name)
        dims = typ.dimensions
        if dims > 0:
            return '%s[%d]' % (name, dims)
        else:
            return name

def jFieldDecl(field_decl):
    for var in field_decl.variable_declarators:
        o = {}
        o['kind'] = 'field'
        o['elem'] = field_decl
        o['type'] = jType(field_decl.type)
        o['name'] = var.variable.name
        o['dims'] = var.variable.dimensions
        o['value'] = var.initializer
        yield o

#------------------------------------------------------------------------------
# Parsing utils.
#------------------------------------------------------------------------------

def iselem(x): return isinstance(x, jmodel.SourceElement)
def isliteral(x): return isinstance(x, jmodel.Literal)
def isadditive(x): return isinstance(x, jmodel.Additive)
def isname(x): return isinstance(x, jmodel.Name)
def isexpr(x): return isinstance(x, jmodel.ExpressionStatement)

def isstrliteral(x):
    if not isliteral(x):
        return False
    return x.value[0] == '"' and x.value[-1] == '"'

def unquote(x):
    if len(x) >= 2:
        if x[0] == '"' and x[-1] == '"':
            return x[1:-1]
    return x

#==============================================================================
# Preprocessor.
#==============================================================================

class Preprocess(object):
    def __init__(self, tree):
        self._tree = tree

    @property
    def tree(self):
        return self.get(self._tree)

    # def merge(self, lhs, rhs):
    #     if isstrliteral(lhs) and isstrliteral(rhs):
    #         return Literal('"' + unquote(lhs.value) + unquote(rhs.value) + '"')

    def get(self, elem):
        if not elem:
            return
        # preprocess each field of the element.
        if iselem(elem):
            for f in elem._fields:
                field = getattr(elem, f)
                if field:
                    if isinstance(field, list):
                        for i in xrange(len(field)):
                            if isinstance(field[i], jmodel.SourceElement):
                                field[i] = self.get(field[i])
                    elif isinstance(field, jmodel.SourceElement):
                        setattr(elem, f, self.get(field))
        if isadditive(elem):
            # if an additive's lhs and rhs are both string literals,
            # then coalesce them.
            if isliteral(elem.lhs) and isliteral(elem.rhs):
                return jmodel.Literal('%s + %s' % (elem.lhs.value, elem.rhs.value))
        return elem

#==============================================================================
# SQLi scanner.
#==============================================================================

class FindSQL(object):
    def __init__(self, ctx):
        self.ctx = ctx

    def find_sqli(self):
        for unit in self.ctx.each_file():
            print 'Scanning %s for SQLi...' % unit
            scanner = FindSQLInUnit(self.ctx, unit)
            scanner.find_sqli()


class FindSQLInUnit(object):
    def __init__(self, ctx, unit):
        self.ctx = ctx
        self.unit = unit

    def find_sqli(self):
        pass


#==============================================================================
# Notes.
#==============================================================================

# print '\n'.join('\n%s:\n\t%s' % (repr(k), repr(v)) for k,v in self.decls.iteritems())



