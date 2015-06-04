import pdb
from ssa.common import *

VERBOSE=False

def scan(files):
    ctx = JavaContext()
    sql_finder = FindSQL(ctx)
    def beforeParsed(filepath, idx, total):
        progress = '(%d/%d)' % (idx, total)
        if g.args.mode == 'syntax':
            print '\n%s %s' % (progress, filepath)
        else:
            print '\n%s %s' % (progress, filepath)
    for unit in parse_files(ctx, files, fnBeforeParsed=beforeParsed):
        if g.args.mode == 'syntax':
            print pp(unit.tree)
        elif g.args.mode == 'sqli':
            sql_finder.search(unit)
        else:
            asserting(False and "unknown mode")

def parse_files(ctx, files, fnBeforeParsed=None):
    files = listify(files)
    for i in xrange(len(files)):
        filepath = files[i]
        if fnBeforeParsed:
            fnBeforeParsed(filepath, idx=i, total=len(files))
        unit = ctx.add_file(filepath)
        if unit:
            yield unit

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
        super(JavaScope, self).__init__(verbose=VERBOSE and isverbose())
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
        val = x.value
        #val = val.replace(r'\n', '\n' + ind(indent))
        val = val.replace(r'\n', '\\n"\n%s"' % ind(indent))
        return 'Literal(%s)' % val
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

def jstr(elem):
    if not elem:
        return None
    if isref(elem):
        return jstr(elem.elem)
    if is_str(elem):
        return elem
    if isname(elem):
        return jName(elem)
    if isstrliteral(elem):
        asserting(hasattr(elem, 'value'))
        asserting(is_str(elem.value))
        return elem.value
    if istype(elem):
        return jType(elem)
    asserting(False)
    return None

def invoke(self, fn, args):
    if self:
        return fn(self, *args)
    else:
        return fn(*args)


def jwalk(elem, fnVisit=None, fnLeave=None, parents=None, idx=0, recursive=True, first=True):
    if not parents:
        parents = []
    ref = ElemRef(elem, parents=list(parents), idx=idx)
    if fnVisit:
        ret = fnVisit(ref)
        if ret:
            return ret
    parents.append(elem)
    childidx = 0
    if recursive or first:
        for f in elem._fields:
            field = getattr(elem, f)
            if field:
                if isinstance(field, list):
                    for i in xrange(len(field)):
                        if isinstance(field[i], jmodel.SourceElement):
                            ret = jwalk(field[i], fnVisit, fnLeave, parents=parents, idx=childidx, recursive=recursive, first=False)
                            childidx += 1
                            if ret:
                                return ret
                elif isinstance(field, jmodel.SourceElement):
                    ret = jwalk(field, fnVisit, fnLeave, parents=parents, idx=childidx, recursive=recursive, first=False)
                    childidx += 1
                    if ret:
                        return ret
    asserting(parents[-1] == elem)
    parents.pop()
    if fnLeave:
        ret = fnLeave(ref)
        if ret:
            return ret

#------------------------------------------------------------------------------
# Parsing utils.
#------------------------------------------------------------------------------

def iselem(x): return isinstance(x, jmodel.SourceElement)
def isliteral(x): return isinstance(x, jmodel.Literal)
def isadditive(x): return isinstance(x, jmodel.Additive)
def isname(x): return isinstance(x, jmodel.Name)
def isexpr(x): return isinstance(x, jmodel.ExpressionStatement)
def isref(x): return isinstance(x, ElemRef)
def istype(x): return isinstance(x, jmodel.Type)
def iscall(x, method_name=None):
    if not isinstance(x, jmodel.MethodInvocation):
        return False
    if method_name:
        return x.name == method_name
    return True

def isstrliteral(x):
    if not isliteral(x):
        return False
    return x.value[0] == '"' and x.value[-1] == '"'

def quote(x):
    # TODO: escape inner quotes.
    return '"' + x + '"'

def unquote(x, optional=False):
    if optional:
        if len(x) >= 2:
            if x[0] == '"' and x[-1] == '"':
                return x[1:-1]
        return x
    else:
        asserting(len(x) >= 2)
        asserting(x[0] == '"' and x[-1] == '"')
        return x[1:-1]

def jmerge(lhs, rhs):
    # if lhs and rhs are both string literals, then combine them.
    if isstrliteral(lhs) and isstrliteral(rhs):
        return jmodel.Literal(quote(unquote(jstr(lhs)) + unquote(jstr(rhs))))

#==============================================================================
# Preprocessor.
#==============================================================================

class Preprocess(object):
    def __init__(self, tree):
        self._tree = tree

    @property
    def tree(self):
        return self.get(self._tree)

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
            merged = jmerge(elem.lhs, elem.rhs)
            if merged:
                return merged
        return elem

#==============================================================================
# Element Reference.
#==============================================================================

def get_parent_expr(parents, idx):
    if not parents:
        return None
    cur = parents[idx]
    asserting(cur)
    if isexpr(cur):
        return idx
    return get_parent_expr(parents, idx - 1)

class ElemRef(object):
    def __init__(self, elem, parents, idx):
        self.elem = elem
        self.parents = list(parents)
        self.idx = idx

    def next_sibling_expr(self, parents=None):
        if not parents:
            parents = list(self.parents)
        if len(parents) <= 0:
            return
        par = parents.pop()
        asserting(par)
        if isadditive(par):
            if par.rhs != self.elem:
                return par.rhs
            return self.next_sibling_expr(parents)
        if iscall(par, 'append'):
            idx = get_parent_expr(parents, idx=-1)
            asserting(idx)
            sibling = jwalk(parents[idx - 1], fnVisit=self._findsib(par), recursive=False)
            return sibling
        if iscall(par):
            return
        if isinstance(par, jmodel.InstanceCreation):
            return
        print '\n\n'
        print '%s!!WARN!!:  %s  %s' % (ind(self.indent), repr(self), repr(par))
        print '\n\n'
        #pdb.set_trace()

    def _findsib(self, of):
        class Finder(object):
            def __init__(self, me, of):
                self.me = me
                self.of = of
                self.found = False

            def find(self, ref):
                elem = ref.elem
                if isexpr(elem):
                    elem = elem.expression
                if iscall(elem, 'append'):
                    if not self.found:
                        if elem.arguments[0] == self.of.arguments[0]:
                            self.found = True
                    else:
                        asserting(elem.arguments[0] != self.of.arguments[0])
                        #pdb.set_trace()
                        return elem.arguments[0]
        return Finder(self, of).find

    @property
    def indent(self):
        return len(self.parents) + 1

    def __str__(self):
        return jstr(self.elem)

    def __repr__(self):
        return pp(self.elem, indent=self.indent + 1)


#==============================================================================
# SQLi scanner.
#==============================================================================
import ssa.sql

class FindSQLInUnit(jmodel.Visitor):
    def __init__(self, unit):
        super(FindSQLInUnit, self).__init__(verbose=VERBOSE and isverbose())
        self.unit = unit
        self.sql = []
        # find SQL statements.
        self.prev_info = None
        jwalk(self.unit.tree, fnVisit=self.visit, fnLeave=self.leave)

    def visit(self, ref):
        if isverbose():
            print '%svisit %s' % (ind(ref.indent), repr(ref))
        if isinstance(ref.elem, jmodel.MethodDeclaration):
            self.prev_info = None

    def leave(self, ref):
        if isverbose():
            print '%sleave %s' % (ind(ref.indent), repr(ref))
        if isstrliteral(ref.elem):
            self.scan_literal(ref)
        if isinstance(ref.elem, jmodel.MethodDeclaration):
            self.prev_info = None

    def scan_literal(self, ref):
        assert(isliteral(ref.elem))
        statements = ssa.sql.findall(str(ref))
        # found if the literal contains any SQL statements
        if len(statements) > 0:
            self.found(ref)
        elif self.prev_info:
            # found if the previous literal contained SQL statements and 
            # ended with any of the following:
            #   =
            #   = '
            #   LIKE '
            # ... and the current literal begins with a matching
            # quote.
            prev = self.prev_info['ref']
            prev_elem = prev.elem
            prev_str = unquote(jstr(prev))
            if len(self.prev_info['sql']) > 0 and ssa.sql.is_ending_vulnerable(prev_str):
                middle = prev.next_sibling_expr()
                if not middle or middle == ref.elem:
                    print '\n\n'
                    print '%s!!SQLI-MAYBE!!:  %s' % (ind(ref.indent), (quote(prev_str) + ' + ' + jstr(ref.elem)))
                    print '\n\n'
                    #pdb.set_trace()
                else:
                    print '\n\n'
                    print '%s!!SQLI!!:  %s' % (ind(ref.indent), (quote(prev_str) + ' + ' + pp(middle) + ' + ' + jstr(ref.elem)))
                    print '\n\n'
                    #pdb.set_trace()

        self.prev_info = {'ref':ref, 'sql':statements}

    def found(self, ref):
        #print '%sFound SQL: %s' % (ind(ref.indent), repr(ref))
        print '%s%s' % (ind(ref.indent), repr(ref))



class FindSQL(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.units = {}

    def search(self, unit):
        if isverbose():
            print 'Scanning %s for SQL statements...' % unit
        self.units[unit.path] = FindSQLInUnit(unit)


#==============================================================================
# Notes.
#==============================================================================

# print '\n'.join('\n%s:\n\t%s' % (repr(k), repr(v)) for k,v in self.decls.iteritems())



