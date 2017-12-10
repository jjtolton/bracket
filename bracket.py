import io
import re
import sys
from functools import reduce
from six import with_metaclass
import naga
from naga import mapv, conj as cons, partition

from lib.utils import to_string, isa


class Symbol(str): pass


def Sym(s, symbol_table={}):
    "Find or create unique Symbol entry for str s in symbol table."
    if s not in symbol_table:
        symbol_table[s] = Symbol(s)
    return symbol_table[s]


_quote, _if, _set, _def, _fn, _begin, _definemacro, = mapv(Sym,
                                                                  "quote   if   set!  def   lambda   begin   define-macro".split())

_quasiquote, _unquote, _unquotesplicing = mapv(Sym,
                                               "quasiquote   unquote   unquote-splicing".split())


class Env(dict):
    "An environment: a dict of {'var':val} pairs, with an outer Env."

    def __init__(self, parms=(), args=(), outer=None):
        # Bind parm list to corresponding args, or single parm to list of args
        self.outer = outer
        if isa(parms, Symbol):
            self.update({parms: list(args)})
        else:
            if len(args) != len(parms):
                raise TypeError('expected %s, given %s, '
                                % (to_string(parms), to_string(args)))
            self.update(zip(parms, args))

    def find(self, var):
        "Find the innermost Env where var appears."
        if var in self:
            return self
        elif self.outer is None:
            raise LookupError(var)
        else:
            return self.outer.find(var)


class SpecialForm:
    def eval(self, env):
        raise NotImplementedError


class Literal:
    def __init__(self, val):
        self.val = val

    def eval(self, _):
        return self.val


class Definition(SpecialForm):
    def __init__(self, name, body):
        self.name = name
        self.body = body

    def eval(self, env):
        env[self.name] = self.body.eval(env)
        return None


class Procedure:
    "A user-defined Scheme procedure."

    def __init__(self, parms, exp, env):
        self.parms, self.exp, self.env = parms, exp, env

    def __call__(self, *args):
        if '.' in self.parms:
            args = list(args)
            idx = self.parms.index('.')
            args = args[:idx] + [args[idx + 1:]]

        return eval(self.exp, Env(self.parms, args, self.env))


class If(SpecialForm):
    def __init__(self, test, exp, alt):
        self.exp = exp
        self.test = test
        self.alt = alt

    def eval(self, env):
        if self.test.eval(env):
            return self.exp.eval(env)
        else:
            return self.alt.eval(env)


class Callable(SpecialForm):
    def __init__(self, proc, args):
        self.proc = proc
        self.args = args

    def eval(self, env):
        exps = [self.proc, *self.args]
        while True:
            proc, *exps = [eval(exp, env) for exp in exps]

            if isa(proc, Procedure):
                x = proc.body
                # TODO: (maybe) scope managed here if issues
                if '.' in proc.parms:
                    idx = proc.parms.index('.')
                    exps = exps[:idx] + [exps[idx:]]
                    parms = proc.parms[:idx] + proc.parms[idx + 1:]
                    env = Env(parms, exps, env)
                else:
                    env = Env(proc.parms, exps, env)
                exps = x
            elif callable(proc):
                return Literal(proc(*exps))
            else:
                return Literal(proc)


class Python(SpecialForm):
    def __init__(self, fname, args):
        self.fname = fname
        self.args = args

    def eval(self, env):
        args = [arg.eval(env) for arg in self.args]
        f = eval(self.fname)
        return f(*args)


class Import(SpecialForm):
    def __init__(self, package):
        self.package = package

    def eval(self, env):
        env[f'{self.package}'] = eval(f'importlib.import_module("{self.package}")', globals(), locals())
        return env[f'{self.package}']


def defn(name, args, exps):
    res = ['def', name, ['fn', args, exps]]
    return res


def let(forms, exps):
    forms = (x for x in list(partition(2, forms))[::-1])

    def _let(forms, exps):
        for a, b in forms:
            return _let(forms, [['fn', [a], exps], b])
        return exps

    res = _let(forms, exps)
    return res


def add_globals(self):
    "Add some Scheme standard procedures."
    import math, cmath, operator as op

    self.update(vars(math))
    self.update(vars(cmath))
    self.update({
        'exit': lambda: sys.exit("Bye!"),
        '+': lambda *args: sum(args) if args else 1,
        '-': lambda *args: reduce(op.sub, args),
        '*': lambda *args: reduce(op.mul, args, 1),
        '/': lambda *args: reduce(op.truediv, args),
        'not': op.not_,
        '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '=': op.eq,
        'equal?': op.eq, 'eq?': op.is_, 'length': len, 'cons': cons,
        'car': lambda x: x[0], 'cdr': lambda x: x[1:], 'append': op.add,
        'list': lambda *x: list(x), 'list?': lambda x: isa(x, list),
        'null?': lambda x: x == [], 'symbol?': lambda x: isa(x, Symbol),
        'boolean?': lambda x: isa(x, bool),
        'apply': lambda proc, l: proc(*l),
        'symbol': lambda x: Symbol(x),
        'count': len,
        'car': lambda x: x[0],
        'cdr': lambda x: x[1:],
        # 'eval': lambda x: eval(expand(x)),
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
        'newline': lambda: print()})
    self.update(vars(naga))
    return self


global_env = add_globals(Env())
eof_object = Symbol('#<eof-object>')  # Note: uninterned; can't be read


class InPort(object):
    "An input port. Retains a line of chars."
    # tokenizer = re.compile(r"""
    #                 \s*(,@                  |  # unquote-splice
    #                     [('`,)]             |  # lparen, quote, quasiquote, unquote, rparen
    #                     "(?:[\\].|[^\\"])*" |  #   multiline string... matches anything between quotes that is
    #                                            ##  \. ---> [\\]. <--- and anything that is not a slash or quote
    #                                            ##     ---> [^\\"]
    #                     ;.*                 |  # comments
    #                     [^\s('"`,;)]*)         # symbols -- match anything that is NOT special character
    #                     |
    #
    #                     (.*) # capture the rest of the string
    #
    #                     """,
    #                        flags=re.X)
    tokenizer = re.compile(r"""\s*([~@]               |
                                   [\["`,\]]          |    # capture [ " ` , ] tokens
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


def repl(prompt='$-> ', inport=InPort(sys.stdin), out=sys.stdout):
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
        except Exception as e:
            print('%s: %s' % (type(e).__name__, e))


# TODO: this more or less defeats the point of protocols, see if we can take this out before it gets out of control
special_forms = {'def': lambda _, name, body: Definition(lex(name, special_forms, macros),
                                                         lex(body, special_forms, macros)),
                 'fn': lambda _, parms, *exps: Procedure(list(map(Symbol, parms)),
                                                         [lex(e, special_forms, macros) for e in exps]),
                 'if': lambda _, cond, exp, alt=None: If(*[lex(e, special_forms, macros) for e in [cond, exp, alt]])}
macros = {'defn': lambda _, name, args, exps: defn(name, args, exps),
          'let': lambda _, forms, exps: let(forms, exps)}


def atom(t):
    if t == '#t':
        return True
    if t == '#f':
        return False

    if t.isdecimal():
        return int(t)

    try:
        return float(t)
    except ValueError:
        pass

    if t.startswith('\'') and t.endswith('\''):
        return t[1:-1]

    return Sym(t)


def lex(t, tables, macros):
    def _lex(t):
        return lex(t, tables, macros)

    if isinstance(t, list):
        if isa(t[0], list):
            return _lex(mapv(_lex, t))
        if t[0] in tables:
            return tables[t[0]](*t)
        if t[0] in macros:
            return _lex(macros[t[0]](*t))

        # callable
        f, *exps = t
        if isa(f, (Procedure, Callable)):
            return Callable(proc=f, args=mapv(_lex, exps))
        else:
            return Callable(proc=Symbol(f), args=mapv(_lex, exps))

    else:
        return atom(t)


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
        elif t is eof_object:
            raise SyntaxError("Unexpected EOF")
        else:
            return atom(t)

    t = next(inport)
    return eof_object if t is eof_object else _read(t)


def parse(x):
    if isa(x, str):
        return parse(InPort(io.StringIO(x)))
    data = read(x)
    return expand(data)


def eval(x, env=global_env):
    "Evaluate an expression in an environment."
    while True:
        if isa(x, Symbol):  # variable reference
            return env.find(x)[x]
        elif not isa(x, list):  # constant literal
            return x
        elif x[0] is _if:  # (if test conseq alt)
            (_, test, conseq, alt) = x
            x = (conseq if eval(test, env) else alt)
        elif x[0] is _def:  # (define var exp)
            (_, var, exp) = x
            env[var] = eval(exp, env)
            return None
        elif x[0] is _fn:  # (lambda (var*) exp)
            (_, vars, exp) = x
            return Procedure(vars, exp, env)
        else:  # (proc exp*)
            exps = [eval(exp, env) for exp in x]
            proc = exps.pop(0)
            if isa(proc, Procedure):
                x = proc.exp

                if '.' in proc.parms:
                    idx = proc.parms.index('.')
                    exps = exps[:idx] + [exps[idx:]]
                    parms = proc.parms[:idx] + proc.parms[idx + 1:]
                    env = Env(parms, exps, proc.env)
                else:
                    env = Env(proc.parms, exps, proc.env)
            else:
                return proc(*exps)


def expand(x):
    if x[0] == 'defn':
        _, name, args, exps = x
        return [_def, name, [_fn, args, exps]]
    return x


# eval(parse('[defn add [. xs] [apply + xs]]'), global_env)
eval(parse('''
[defn add [res xs]
    [if [= 0 [count xs]]
        res
        [add [+ res [car xs]] 
             [cdr xs]]]]'''))

# eval(parse('[add 0 [list 1 2 3]]'), global_env)

if __name__ == '__main__':
    repl()
