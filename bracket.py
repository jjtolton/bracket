import io
import itertools
import re
import sys
from functools import reduce

import naga
from naga import mapv, conj as cons, partition, append, drop

from lib.destructure import destructure
from lib.macros import macro_table, let
from lib.special_forms import KeyWord
from lib.symbols import fn_, unquotesplicing_, append_, cons_, PyObject
from lib.symbols import unquote_, defmacro_, Symbol, quote_, if_, def_, begin_, quasiquote_
from lib.utils import to_string, isa, ara


class Env(dict):
    """An environment: a dict of {'var':val} pairs, with an outer Env."""

    def __init__(self, parms=(), args=(), outer=None, name=None):
        # Bind parm list to corresponding args, or single parm to list of args
        self.outer = outer
        if isa(parms, Symbol):
            self.update({parms: list(args)})
        else:

            def recursive_eval(x, env):
                try:
                    if isa(x, list):
                        return [eval(xi, env) for xi in x]
                except Exception as e:
                    return x

            bindings = partition(2, destructure(list(append(*itertools.zip_longest(parms, args)))))

            for k, v in bindings:
                try:
                    self.update({k: eval(v, self)})
                except Exception:
                    self.update({k: v})

                    # (self.update({k: eval(v, self)}) if isa(v, list) else
                    #  self.update({k: v}))

                    # self.update({k: v for k, v in })
                    # self.update(zip(parms, args))

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


class Proc:
    "A user-defined Scheme procedure."

    def __init__(self, parms, exp, env):
        self.parms, self.exp, self.env = parms, [begin_, *exp], env

    def __call__(self, *args):
        self.exp = let(list(zip(self.parms, list(args))), self.exp)
        return eval(self.exp, Env(self.parms, args, self.env))


class Procedure:
    def __init__(self, env, forms):
        self.procs = []
        self.variadic = None
        for form in forms:
            args, *exps = form
            if '.' in args:
                self.variadic = Proc(args, exps, env)
            self.procs.append(Proc(args, exps, env))

            # self.procs = [Proc(*(*form, *[env])) for form in forms]

    def __call__(self, *args):
        return self.proc(*args)(*args)

    def proc(self, *args):
        for p in self.procs:
            if len(p.parms) == len(args):
                return p
        else:
            return self.variadic

            # def apply(self, *x):
            #     lst = x[-1]
            #     if isa(lst, list):
            #         a = x[:-1]
            #         y = a + lst
            #         return self(*y)
            #
            #     return self(*x)


def add_globals(self):
    "Add some Scheme standard procedures."
    import operator as op

    self.update({
        'exit': lambda: sys.exit("Bye!"),
        '+': lambda *args: sum(args) if args else 1,
        '-': lambda *args: reduce(op.sub, args),
        '*': lambda *args: reduce(op.mul, args, 1),
        '/': lambda *args: reduce(op.truediv, args),
        'not': op.not_,
        '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '=': op.eq,
        'equal?': op.eq, 'eq?': op.is_, 'length': len, 'cons': cons,
        'car': lambda x: x[0],
        'cdr': lambda x: x[1:],
        'append': op.add,
        'list': lambda *x: list(x), 'list?': lambda x: isa(x, list),
        'null?': lambda x: x == [], 'symbol?': lambda x: isa(x, Symbol),
        'boolean?': lambda x: isa(x, bool),
        'symbol': lambda x: Symbol(x),
        'count': len,
        'eval': lambda x: eval(expand(x)),
        # 'load': lambda fn: load(fn),

        # 'call/cc': callcc,
        'open-input-file': open,
        'range': lambda *args: list(range(*args)),
        'close-input-port': lambda p: p.file.close(),
        'open-output-file': lambda f: open(f, 'w'),
        'close-output-port': lambda p: p.close(),
        'eof-object?': lambda x: x is eof_object,
        # 'read-char': readchar,
        # 'read': read,
        # 'write': lambda x, port=sys.stdout: port.write(to_string(x)),
        'print': lambda x: print(x),
        'pformat': lambda s, *args: print(s.format(*args)),
        'display': lambda x, port=sys.stdout: port.write(x if isa(x, str) else to_string(x)),
        'newline': lambda: print(),
        '.': lambda k, v: getattr(k, v),
        'dropv': lambda *args: list(drop(*args)),
    })
    self.update(vars(naga))

    def apply(f, *x):
        lst = x[-1]
        if isa(lst, (list, tuple, str)):
            a = list(x[:-1])
            args = a + list(lst)
        else:
            args = x
        return f(*args)

    self.update({'apply': apply})

    def import_(n):
        if isa(n, Symbol):
            package = Env(name=n)
            for k, v in vars(__import__(n, globals(), locals())).items():
                package[k] = v
            self[n] = package
        if isa(n, list):
            name, *args = n
            import__ = __import__(name, globals(), locals())
            if len(args) == 1 and args[0] == '*':
                for k, v in vars(import__).items():
                    global_env[k] = v
            else:
                for arg in args:
                    global_env[arg] = import__[arg]




    self.update({'import': import_})

    def require(n):

        if isa(n, (Symbol, str)):
            fname = f'{n}.br'
            new_env = Env(name=n, outer=global_env)
            with open(fname) as f:
                eval(parse(f.read()), new_env)
            self[n] = new_env
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
                temp_env = Env(outer=global_env)
                with open(name) as f:
                    contents = f.read()
                    eval(parse(contents), temp_env)

                    for k in temp_env:
                        global_env[k] = temp_env[k]

    self.update({'require': require})
    return self


global_env = add_globals(Env(__name__))

eof_object = Symbol('#<eof-object>')  # Note: uninterned; can't be read


class InPort(object):
    "An input port. Retains a line of chars."
    tokenizer = re.compile(r"""\s*([~@]               |
                                   [\[/`,\]]          |    # capture [ " ` , ] tokens
                                   '(?:[\\].|[^\\'])*'|    # strings
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


def repl(prompt='$-> ', inport=InPort(sys.stdin), out=sys.stdout, debug=False):
    "A prompt-read-eval-print loop."
    while True:
        try:
            if prompt:
                print(prompt, end=' ', flush=True)
            x = parse(inport)
            if x is eof_object:
                return
            val = eval(x)
            if val is not None and out:
                output = to_string(val)
                print(f';;=> {output}', file=out)
        except KeyboardInterrupt:
            print()
            continue
        except Exception as e:
            print('%s: %s' % (type(e).__name__, e))
            if debug is True:
                raise e


def atom(t):
    if t == '#t':
        return True
    if t == '#f':
        return False

    if t.isdecimal() or t.startswith('-') and t[1:].isdecimal():
        return int(t)

    try:
        return float(t)
    except ValueError:
        pass

    if t.startswith('-'):
        return KeyWord(t[1:])

    if t.startswith('\'') and t.endswith('\''):
        return t[1:-1]

    if t.startswith('py/'):
        return PyObject(t[3:])

    return Symbol(t)


quotes = {'/'}


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
            return [quote_, read(inport)]
        elif t is eof_object:
            raise SyntaxError("Unexpected EOF")
        else:
            return atom(t)

    t = next(inport)

    return eof_object if t is eof_object else _read(t)


def parse(x):
    if isa(x, str):
        return parse(InPort(io.StringIO(f'[begin {x}]')))
    data = read(x)
    return expand(data)


def eval(x, env=global_env):
    "Evaluate an expression in an environment."
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
        elif x[0] == defmacro_:
            _, v, body = x
            macro_table[v] = eval(body)
            return None

        elif x[0] == 'quote':
            (_, exp) = x
            return exp
        elif x[0] == 'fn':  # (lambda (var*) exp)
            if len(x) > 2:
                (_, *exp) = x
                exp = [list(exp)]
            else:
                (_, exp) = x
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
                    x[-1] = str(x[-1])

            exps = [eval(exp, env) for exp in x]
            proc = exps.pop(0)

            if isa(proc, Procedure):
                x = proc.proc(*exps)
                proc = x

            if isa(x, Proc):
                x = proc.exp
                # if '.' in proc.parms:
                #     idx = proc.parms.index('.')
                #     exps = exps[:idx] + [exps[idx:]]
                #     parms = proc.parms[:idx] + proc.parms[idx + 1:]
                #     env = Env(parms, exps, proc.env)
                # else:
                env = Env(proc.parms, exps, proc.env)

            else:
                return proc(*exps)


def require(x, predicate, msg="wrong length"):
    "Signal a syntax error if predicate is false."
    if not predicate: raise SyntaxError(to_string(x) + ': ' + msg)


def expand(x, toplevel=False):
    "Walk tree of x, making optimizations/fixes, and signaling SyntaxError."
    require(x, x != [])  # () => Error
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
    elif x[0] is def_ or x[0] is defmacro_:
        require(x, len(x) >= 3)
        _d, v, body = x[0], x[1], x[2]
        exp = expand(body)
        # if _d is defmacro_:
        #     require(x, toplevel, "define-macro only allowed at top level")
        #     proc = eval(exp)
        #     require(x, callable(proc), "macro must be a procedure")
        #     macro_table[v] = proc  # (define-macro v proc)
        #     return None  # => None; add v:proc to macro_table
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
            exp = [[args, [begin_, *mapv(expand, xi)]] for args, *xi in body]
        # @formatter:on

        # simple style
        else:
            args, *xi = body
            exp = [[args, [begin_, *mapv(expand, xi)]]]

        return [fn_, exp]

    elif x[0] is quasiquote_:  # `x => expand_quasiquote(x)
        require(x, len(x) == 2)
        return expand_quasiquote(x[1])

    elif isa(x[0], Symbol) and x[0] in macro_table:
        name = x[0]
        body = x[1:]
        res = expand(macro_table[name](*body), toplevel)
        return res  # (m arg...)

    # elif isa(x[0], list):
    #     parms, *body = x
    #     return [parms, *mapv(expand, body)]

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
    elif is_pair(x[0]) and x[0][0] is unquotesplicing_:
        require(x[0], len(x[0]) == 2)
        return [append_, x[0][1], expand_quasiquote(x[1:])]
    else:
        return [cons_, expand_quasiquote(x[0]), expand_quasiquote(x[1:])]


def special_functions():
    try:
        eval(parse('[import [math *]]'))
        eval(parse('[import [cmath *]]'))
        eval(parse('[require [stdlib *]]]'))

    except FileNotFoundError:
        print('cannot find stdlib')


if __name__ == '__main__':
    special_functions()
    if __debug__:
        repl(debug=True)
    else:
        repl()
