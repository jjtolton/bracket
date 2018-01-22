import io
import itertools
import re
import types
from functools import partial

from naga import mapv, partition

from lib.core import div, nil
from lib.destructure import destruct
from lib.macros import macro_table, _let, defn
from lib.special_forms import KeyWord
from lib.symbols import Symbol, PyObject, quote_, quasiquote_, unquote_, unquotesplicing_, do_, append_, cons_, \
    autogensym_, let_, defmacro_
from lib.utils import isa, to_string, ara, AutoGenSym

gensym = AutoGenSym()


class InPort(object):
    "An input port. Retains a line of chars."
    tokenizer = re.compile(r"""\s*(,-                 |    # quasiquote
                                   [\[/`,\]]          |    # capture [ " ` , ] tokens
                                   '(?:[\\].|[^\\'])*'|    # strings
                                     {.*?}            |    # future map literal
                                   ;.*|                    # single line comments
                                   [^\s\['"`,;\]]*)        # match everything that is NOT a special character
                                   (.*)                    # match the rest of the string""",

                           flags=re.VERBOSE)

    def __init__(self, file):
        self.file = file
        self.line = ''

    def next_token(self):
        "Return the next token, reading new text into line buffer if needed."
        while True:
            if self.line == '':
                self.line = self.file.readline()
            if self.line == '':
                return eof_object
            token, self.line = re.match(InPort.tokenizer, self.line).groups()
            if token != '' and not token.startswith(';'):
                return token

    def __iter__(self):
        t = next(self)
        while t != eof_object:
            yield t
            t = next(self)

    def __next__(self):
        return self.next_token()


class Env(dict):
    """An environment: a dict of {'var':val} pairs, with an outer Env."""

    def __init__(self, parms: (tuple, list) = (), args: (tuple, list) = (), outer: dict = None, name: str = None, macro: bool=False):
        self.name = name
        self.outer = outer

        bindings = destruct(parms, args, ag=gensym)
        if len(bindings) == 0:
            return
        parms, args = list(zip(*bindings))
        if macro is False:
            for parm, arg in zip(parms, args):
                self[parm] = eval(arg, self)
        elif macro is True:
            for parm, arg in zip(parms, args):
                if parm not in parms:
                    self[parm] = eval(arg, self)
                else:
                    self[parm] = arg


    def find(self, var, not_found=nil):
        """Find the innermost Env where var appears."""
        if '/' in var:
            n, m = var.split('/', maxsplit=1)
            return self.find(n)[n].find(m)

        if var in self:
            return self
        elif self.outer is None:
            if not_found is nil:
                raise LookupError(f"Symbol `{var} is undefined")
            else:
                return not_found
        else:
            return self.outer.find(var, not_found=not_found)


def import_(global_env, imports, name=None):
    if isa(imports, (Symbol, str)):
        if name is None:
            name = imports

        package = Env(name=name)
        for k, v in vars(__import__(imports, globals(), locals(),
                                    fromlist=imports.split('.')[:-1])).items():
            package[k] = v
        global_env[name] = package

    if isa(imports, list):
        import_name, *args = imports
        import__ = __import__(import_name, globals(), locals(),
                              fromlist=import_name.split('.')[:-1])

        if len(args) == 1 and args[0] == '*':
            for k, v in vars(import__).items():
                global_env[k] = v
        else:
            for arg in args:
                global_env[arg] = vars(import__)[arg]


def require_(global_env, n, name=None):
    if isa(n, (Symbol, str)):
        if name is None:
            name = n

        fname = f'{n}.br'
        new_env = Env(name=n, outer=global_env)
        with open(fname) as f:
            eval(parse(f.read()), new_env)
        global_env[name] = new_env
    if isa(n, list):
        if n[0] == 'from':
            name = f'{n[1]}.br'
            items = n[2]
        else:
            name = f'{n[0]}.br'
            items = n[1]
        if isa(items, list):
            temp_env = Env(outer=global_env)
            with open(name) as f:
                contents = f.read()
                eval(parse(contents), temp_env)

                for item in items:
                    global_env[item] = temp_env[item]
        if items == '*':
            # temp_env = Env(outer=global_env)
            with open(name) as f:
                for x in read(f.read())[1:]:
                    try:
                        eval(x, global_env)
                    except Exception as e:
                        print(f'unable to parse {x}')
                return None


eof_object = Symbol('#<eof-object>')  # Note: uninterned; can't be read


def atom(t):
    if t == 'true':
        return True
    if t == 'false':
        return False

    if t.isdecimal() or t.startswith('-') and t[1:].isdecimal():
        return int(t)

    if re.match('^[-]?\d+?[.]\d*?$', t):
        return float(t)

    if t.startswith('-') and len(t[1:]) > 0:
        return KeyWord(t[1:])

    if t.startswith('\'') and t.endswith('\''):
        return t[1:-1]

    if t.startswith('py/'):
        return PyObject(t[3:])

    if t.endswith('#'):
        return [autogensym_, t[:-1]]

    return Symbol(t)


# @formatter:off
quotes = {"/":  quote_,
          "`":  quasiquote_,
          ",":  unquote_,
          ",-": unquotesplicing_}
# @formatter:on


def read(inport: (type(InPort), str)):
    if isa(inport, str):
        return read(InPort(io.StringIO(f'[do {inport}]')))

    def _read(t):
        res = []
        if t == '[':
            while True:
                t = next(inport)
                if t == ']':
                    return res
                else:
                    res.append(_read(t))
        elif t == ']':
            raise Exception("unmatched delimiter: ]")
        elif t in quotes:
            return [quotes[t], read(inport)]
        elif t is eof_object:
            raise SyntaxError("Unexpected EOF")
        else:
            return atom(t)

    token = next(inport)

    return eof_object if token is eof_object else _read(token)


def parse(x):
    data = read(x)
    return data


user_macros = {}


class Proc:
    "A user-defined Scheme procedure."

    def __init__(self, parms, exp, env):
        self.parms, self.exp, self.env = parms, [do_, *exp], env

    def __call__(self, *args, **kwargs):
        return eval(self.exp, Env(self.parms, args, self.env))


class Procedure:
    def __init__(self, env, forms, name, doc, opts, source):
        self.source = source
        self.opts = opts
        self.doc = doc
        self.name = name
        self.procs = {}
        self.variadic = None
        for form in forms:
            args, *exps = form
            if '.' in args:
                self.variadic = Proc(args, exps, env)
                continue
            self.procs[len(args)] = Proc(args, exps, env)

    def __call__(self, *args):
        p = self.proc(*args)
        return p(*args)

    def proc(self, *args):
        return self.procs.get(len(args), self.variadic)

    def __repr__(self):
        return f'<function.{self.name}>'


class Mac(Proc):

    def __call__(self, *args, **kwargs):
        return eval(self.exp, Env(self.parms, args, outer=self.env, macro=True))
    # def __call__(self, *args):
    #     parms = self.parms
    #     exp = self.exp
    #     env = self.env
    #     if len(parms) == 0:
    #         res = eval(exp, Env(self.parms, args, env))
    #     else:
    #         argsubs = [gensym('parm__') for _ in parms]
    #         bindings, args = zip(*itertools.chain(zip(argsubs, args), zip(parms, argsubs)))
    #
    #         bindings = destruct(bindings, args, ag=gensym)
    #         new_env = Env(outer=env)
    #         for parm, arg in partition(2, bindings):
    #             if parm not in argsubs:
    #                 new_env[parm] = eval(arg, new_env)
    #             else:
    #                 new_env[parm] = arg
    #
    #         res = eval(exp, new_env)
    #
    #     return res


class Macro(Procedure):
    def __init__(self, env, forms, name, doc, opts, source):
        self.source = source
        self.opts = opts
        self.doc = doc
        self.name = name
        self.procs = {}
        self.variadic = None
        for form in forms:
            parms, *exps = form
            if '.' in parms:
                self.variadic = Mac(parms, exps, env)
            self.procs[len(parms)] = Mac(parms, exps, env)

    def __repr__(self):
        return f'<macro.{self.name}>'


global_env = Env(name=__name__)


def alldiff(xs):
    return len(set(xs)) != len(list(xs))


def compoundfn(x):
    if not ara(x, list):
        return False
    if not ara([xi[0] for xi in x], list):
        return False
    if not alldiff(len(xi[0]) for xi in x):
        return False
    return True


def eval(x, env=global_env):
    "Evaluate an expression in an environment."
    try:
        while True:

            # base case 1: binding
            if isa(x, Symbol):  # variable reference


                loc = env.find(x, not_found=False)
                if loc:
                    if '/' in x:
                        return loc[x.split('/')[-1]]
                    else:
                        return loc[x]

                elif macro_table.get(x):
                    return macro_table[x]
                else:
                    raise ValueError(f'Symbol({x}) is undefined')

            elif not isa(x, list) or isa(x, list) and len(x) == 0:  # constant literal
                return x
            elif x[0] == 'if':  # (if test conseq alt)
                (_, test, conseq, alt) = x
                x = (conseq if eval(test, env) not in (None, False, nil) else alt)

            elif x[0] == defmacro_:
                # compound form only!!
                # require(x[1:], compoundfn, msg="Compound form required for macro")
                # require(x, toplevel, "define-macro only allowed at top level")

                source = x[:]
                # remove fn tag
                _, *x = x
                # x.pop(0)
                # (defmacro opts name [*args] *body)

                if isa(x[0], Symbol):
                    name, *x = x
                else:
                    name = gensym('fn__')

                if isa(x[0], str):
                    doc, *x = x
                else:
                    doc = 'No docstring'

                if isa(x[0], dict):
                    opts, *x = x
                else:
                    opts = {}

                """[[args] <body> ] [[args] <body>] ...] or
                [args] <body> ...]"""
                if compoundfn(x):
                    exp = x
                else:
                    exp = [x]

                macro = Macro(env, exp, name, doc, opts, source)
                # require(x, callable(proc), "macro must be a procedure")
                macro_table[name] = macro  # (define-macro v proc)
                return None  # => None; add v:proc to macro_table

            elif x[0] == 'def':  # (define var exp)
                (_, var, exp) = x
                env[var] = eval(exp, env)
                return None

            elif x[0] == do_:
                for exp in x[1:-1]:
                    eval(exp, env)
                x = x[-1]

            elif x[0] == quasiquote_:
                x = expand_quasiquote(x[1])
                continue

            elif x[0] == 'quote':
                (_, exp) = x
                return exp

            elif x[0] == 'fn':  # (lambda (var*) exp)
                # [fn name? doc? opts? body]
                # body -> simple  [.. [*args] body]
                #      -> complex [.. [[*args0] body0]]  [[*args1] [body1]]
                source = x[:]
                # remove fn tag
                _, *x = x
                # x.pop(0)
                # (fn opts name [*args] *body)

                if isa(x[0], Symbol):
                    name, *x = x
                else:
                    name = gensym('fn__')

                if isa(x[0], str):
                    doc, *x = x
                else:
                    doc = 'No docstring'

                if isa(x[0], dict):
                    opts, *x = x
                else:
                    opts = {}

                # possibilities
                # [fn opts? name? doc? [x] x]
                # [fn opts? name? [destructured] x]
                # [fn

                """[[args] <body> ] [[args] <body>] ...] or
                [args] <body> ...]"""
                if compoundfn(x):
                    exp = x
                else:
                    exp = [x]

                return Procedure(Env(outer=env), exp, name, doc, opts, source)


            else:  # (proc exp*)

                if x[0] in ('require', 'import'):
                    if isa(x[-1], list):  # [require stdlib *]
                        x[-1] = [quote_, x[-1]]
                    else:
                        x[1:] = [[quote_, e] for e in x[1:]]

                name, args = eval(x[0], env), x[1:]
                # procedure evaluation

                if isa(name, Procedure) and not isa(name, Macro):
                    procedure = name
                    proc = procedure.proc(*args)
                    e = Env()
                    e.update(env)
                    e.update(proc.env)
                    env = Env(proc.parms, args, Env(outer=e))
                    x = proc.exp
                    continue

                elif isa(name, Macro):
                    macro = name
                    mac = macro.proc(*args)
                    x = mac(*args)
                    continue

                elif isa(x[0], Symbol) and x[0] in macro_table:
                    x = name(*args)
                    continue

                elif isinstance(name, (types.FunctionType, types.MethodType)):
                    f = name
                    args = mapv(partial(eval, env=env), args)
                    return f(*args)


                elif callable(name):
                    f = name
                    args = mapv(partial(eval, env=env), args)
                    return f(*args)

                # literal
                return x
    except Exception as e:
        try:
            raise e
        finally:
            print("Bad form: {}".format(x))


def require(x, predicate, msg="wrong length"):
    "Signal a syntax error if predicate is false."
    if not predicate: raise SyntaxError(to_string(x) + ': ' + msg)


def is_pair(x): return x != [] and isa(x, list)


def expand_quasiquote(x):
    """Expand `x => 'x; `,x => x; `(,@x y) => (append x y) """
    if not is_pair(x):
        return [quote_, x]
    require(x, x[0] is not unquotesplicing_, "can't splice here")
    if x[0] is unquote_:
        require(x, len(x) == 2)
        return x[1]
    if x[0] is autogensym_:
        return AutoGenSym()(x[1])
    elif is_pair(x[0]) and x[0][0] is unquotesplicing_:
        require(x[0], len(x[0]) == 2)
        return [append_, x[0][1], expand_quasiquote(x[1:])]
    else:
        return [cons_, expand_quasiquote(x[0]), expand_quasiquote(x[1:])]


def special_functions():
    try:
        global_env['import'] = partial(import_, global_env)
        global_env['require'] = partial(require_, global_env)
        global_env['eval'] = eval
        global_env['destructure'] = lambda x: destruct(*zip(*x))
        global_env['/'] = div
        global_env['*env*'] = global_env
        global_env['*mac*'] = macro_table

        eval(parse('[require [core *]]]'), global_env)

        def macroexpand(x):
            x = eval(x, global_env)
            macro, args = macro_table[x[0]], x[1:]

            if isa(macro, Macro):
                for p in macro.procs:
                    if len(p.parms) == len(args):
                        mac = p
                        break
                else:
                    mac = macro.variadic

                parms = mac.parms
                mac_env = Env(outer=mac.env)
                args = [[quote_, arg] for arg in args]

                bindings = destruct(parms, args, ag=gensym)
                for parm, arg in bindings:
                    res = eval(arg, mac_env)
                    mac_env[parm] = res

                x = mac.exp
                return x

            else:
                # Python-defined macro
                x = macro(*args)
                return x

        global_env['macroexpand'] = macroexpand

    except FileNotFoundError:
        print('cannot find stdlib')
