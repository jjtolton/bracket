import io
import re
from functools import partial

from naga import mapv, partition

from lib.destructure import destruct
from lib.macros import defn, macro_table, _let, let
from lib.special_forms import KeyWord
from lib.stdlib import div
from lib.symbols import Symbol, PyObject, quote_, quasiquote_, unquote_, unquotesplicing_, begin_, if_, def_, defmacro_, \
    fn_, append_, cons_, autogensym_
from lib.utils import isa, to_string, ara, flatten, AutoGenSym


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

    def __init__(self, parms=(), args=(), outer=None, name=None, macro=False):
        # Bind parm list to corresponding args, or single parm to list of args

        if macro is True:
            self.outer = outer
            if isa(parms, Symbol):
                self.update({parms: list(args)})
            else:
                if len(args) != len(parms):
                    raise TypeError('expected %s, given %s, '
                                    % (to_string(parms), to_string(args)))
                self.update(zip(parms, args))
        else:
            self.outer = outer

            bindings = destruct(parms, args)
            fparms = set(flatten(parms)) - {'.'}

            for k, v in bindings:
                if isa(k, (list, Symbol)):
                    try:
                        if isa(v, list) and len(v) > 0 and not isa(v[0], list) and self.find(v[0]) and k not in fparms:
                            self.update([(k, eval(v, self))])
                        else:
                            self.update([(k, v)])

                    except Exception as e:
                        if __debug__ is True:
                            print(e)
                        self.update([(k, v)])
                else:
                    self.update([(k, v)])

                    # try:
                    #     self.update({k: eval(v, self)})
                    # except Exception:

    def find(self, var):
        """Find the innermost Env where var appears."""
        if '/' in var:
            n, m = var.split('/')
            return self.find(n).find(m)

        if var in self:
            return self
        elif self.outer is None:
            raise LookupError(var)
        else:
            return self.outer.find(var)


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
                contents = f.read()
                return eval(parse(contents), global_env)


eof_object = Symbol('#<eof-object>')  # Note: uninterned; can't be read


def atom(t):
    if t == 'true':
        return True
    if t == 'false':
        return False

    if t.isdecimal() or t.startswith('-') and t[1:].isdecimal():
        return int(t)

    try:
        return float(t)
    except ValueError:
        pass

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


def read(inport: type(InPort)):
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
    if isa(x, str):
        return parse(InPort(io.StringIO(f'[begin {x}]')))
    data = read(x)
    return expand(data)


user_macros = {}


class Proc:
    "A user-defined Scheme procedure."

    def __init__(self, parms, exp, env):
        self.parms, self.exp, self.env = parms, [begin_, *exp], env

    def __call__(self, *args):
        let1 = _let(self.parms, list(args), self.exp)
        return eval(let1, Env(self.parms, args, self.env))


class Procedure:
    def __init__(self, env, forms):
        self.procs = []
        self.variadic = None
        for form in forms:
            args, *exps = form
            if '.' in args:
                self.variadic = Proc(args, exps, env)
            self.procs.append(Proc(args, exps, env))

    def __call__(self, *args):
        p = self.proc(*args)
        return p(*args)

    def proc(self, *args):
        for p in self.procs:
            if len(p.parms) == len(args):
                return p
        else:
            return self.variadic


class ApplicationContext:
    @staticmethod
    def expand_exp(env, x):
        proc = eval(x.pop(0), env)
        return proc, x

    @classmethod
    def __enter__(cls):
        globals().update(cls.new)

    @classmethod
    def __exit__(cls, exc_type, exc_val, exc_tb):
        globals().update(cls.old)


def expand_exp(env, x):
    exps = [eval(exp, env) for exp in x]
    proc = exps.pop(0)
    return proc, exps


class Mac(Proc):
    def __call__(self, *args, **kwargs):
        if '.' in self.parms:
            args = list(args)
            idx = self.parms.index('.')
            args = args[:idx] + [args[idx:]]
            # TODO: possible trouble spot
            parms = self.parms[:idx] + self.parms[idx+1:]
        else:
            parms = self.parms

        return eval(self.exp, Env(parms, args, self.env, macro=True))


class Macro(Procedure):
    def __init__(self, env, forms):
        self.procs = []
        self.variadic = None
        for form in forms:
            args, *exps = form
            if '.' in args:
                self.variadic = Mac(args, exps, env)
            self.procs.append(Mac(args, exps, env))


class MacroContext(ApplicationContext):
    def __init__(self):
        self.old = {Procedure.__name__: Procedure,
                    Proc.__name__: Proc,
                    expand_exp.__name__: expand_exp}

        self.new = {Procedure.__name__: Macro,
                    Proc.__name__: Mac,
                    expand_exp.__name__: self.old[expand_exp.__name__]}

    @staticmethod
    def expand_exp(env, x):
        proc = eval(x.pop(0), env)
        return proc, x

    def __enter__(self):
        globals().update(self.new)

    def __exit__(self, exc_type, exc_val, exc_tb):
        globals().update(self.old)


class ProcedureContext(ApplicationContext):
    new = {Procedure.__name__: Procedure,
           Proc.__name__: Proc,
           expand_exp.__name__: expand_exp}

    old = {}


global_env = Env(name=__name__)


def eval(x, env=global_env, toplevel=False):
    "Evaluate an expression in an environment."
    # if toplevel is True:
    #     return eval(expand(x), env)

    while True:
        if isa(x, Symbol):  # variable reference
            if '/' in x:
                n, m = x.split('/')
                return env.find(n)[n][m]
            else:
                return env.find(x)[x]

        elif not isa(x, list):  # constant literal
            return x
        elif x[0] == 'if':  # (if test conseq alt)
            (_, test, conseq, alt) = x
            x = (conseq if eval(test, env) else alt)
        elif x[0] == 'def':  # (define var exp)
            (_, var, exp) = x
            env[var] = eval(exp, env)
            return None
        elif x[0] == begin_:
            for exp in x[1:-1]:
                eval(exp, env)
            x = x[-1]

        elif x[0] == 'quote':
            (_, exp) = x
            return exp
        elif x[0] == 'fn':  # (lambda (var*) exp)
            if len(x) > 2:
                (_, *exp) = x
                exp = [list(exp)]
            else:
                (_, exp) = x
            # with ProcedureContext():
            return Procedure(env, exp)
        elif x[0] is quote_:
            _, q = x
            return q


        else:  # (proc exp*)

            if x[0] == '.':
                x[-1] = str(x[-1])

            if x[0] in ('require', 'import'):
                if isa(x[-1], list):  # [require stdlib *]
                    x[-1] = [quote_, x[-1]]
                else:
                    x[1:] = [[quote_, e] for e in x[1:]]

            proc, exps = expand_exp(env, x)

            if isa(proc, Procedure):
                x = proc.proc(*exps)
                proc = x

            if isa(x, Proc):
                x = proc.exp
                env = Env(proc.parms, exps, proc.env)
                continue

            if callable(proc):
                return proc(*exps)

            # TODO: danger zone! put this hack in to help deal with macros
            return [proc, *exps]


def require(x, predicate, msg="wrong length"):
    "Signal a syntax error if predicate is false."
    if not predicate: raise SyntaxError(to_string(x) + ': ' + msg)


def expand(x, toplevel=False):
    "Walk tree of x, making optimizations/fixes, and signaling SyntaxError."
    # require(x, x != [])  # () => Error
    if x == []:
        return [quote_, x]
    if not isa(x, list):  # constant => unchanged
        return x
    elif x[0] is quote_:  # (quote exp)
        require(x, len(x) == 2)
        return x
    elif x[0] is if_:
        if len(x) == 3:
            x = x + [None]  # (if t c) => (if t c None)
        require(x, len(x) == 4)
        return mapv(expand, x)
    elif x[0] is quote_:
        return x
    elif x[0] == def_ or x[0] == defmacro_:
        require(x, len(x) >= 3)
        _d, v, body = x[0], x[1], x[2]
        if _d == defmacro_:
            _, _, body = expand(defn(*x[1:]))
            # require(x, toplevel, "define-macro only allowed at top level")
            with MacroContext():
                proc = eval(body)
            require(x, callable(proc), "macro must be a procedure")
            macro_table[v] = proc  # (define-macro v proc)
            return None  # => None; add v:proc to macro_table
        exp = expand(body)
        return [_d, v, exp]

    elif x[0] is begin_:
        if len(x) == 1:
            return None  # (begin) => None
        else:
            return [expand(xi, toplevel) for xi in x]

    elif x[0] == fn_:  # (lambda (x) e1 e2)
        body = x[1:]

        # body can either be of simple style [fn [x] x] or [fn [x] [f x]] or [fn [x] [f x] [g x]]
        # compound style                     [fn [[a] a]] [[a b] ...] [[a b c] ... ]]

        # compound style
        # @formatter:off
        if (ara(body, list)                 and
            all(isa(e, list) for e in body) and
            len(body[0]) > 0                and
            all(isa(e[0], list) for e in body)):
            exp = [[args, *mapv(expand, xi)] for args, *xi in body]
        # @formatter:on

        # simple style
        else:
            args, *xi = body
            exp = [[args, *mapv(expand, xi)]]

        return [fn_, exp]

    elif x[0] is quasiquote_:  # `x => expand_quasiquote(x)
        require(x, len(x) == 2)
        return expand_quasiquote(x[1])

    elif isa(x[0], Symbol) and x[0] in macro_table:
        name = x[0]
        body = x[1:]
        # print(f'body: {body})')
        res = expand(macro_table[name](*body), toplevel)
        return res  # (m arg...)

    else:  # => macroexpand if m isa macro
        return mapv(expand, x)  # (f arg...) => expand each


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
        global_env['expand'] = expand
        global_env['destructure'] = lambda x: destruct(*zip(*x))
        global_env['/'] = div

        eval(parse('[import [math *]]'))
        eval(parse('[import [cmath *]]'))
        eval(parse('[require [stdlib *]]]'))

        def macroexpand(form):
            name, *body = form
            return macro_table[name](*body)

        global_env['macroexpand'] = macroexpand

        del global_env['lib']
    except FileNotFoundError:
        print('cannot find stdlib')
