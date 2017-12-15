import io
import re
import sys
from functools import reduce

import naga
from naga import mapv, conj as cons

from lib.destructure import destruct, prestruct
from lib.macros import macro_table
from lib.symbols import fn_, unquotesplicing_, append_, cons_, KeyWord
from lib.symbols import unquote_, defmacro_, Symbol, quote_, if_, def_, begin_, quasiquote_
from lib.utils import to_string, isa


class Env(dict):
    """An environment: a dict of {'var':val} pairs, with an outer Env."""

    def __init__(self, parms=(), args=(), outer=None):
        # Bind parm list to corresponding args, or single parm to list of args
        self.outer = outer
        if isa(parms, Symbol):
            self.update({parms: list(args)})
        else:
            self.update({k: v for k, v in naga.partition(2, prestruct(parms, args))})
            # self.update(zip(parms, args))

    def find(self, var):
        """Find the innermost Env where var appears."""
        if var in self:
            return self
        elif self.outer is None:
            raise LookupError(var)
        else:
            return self.outer.find(var)


class Proc:
    "A user-defined Scheme procedure."

    def __init__(self, parms, exp, env, parent):
        self.parms, self.exp, self.env, self.parent = parms, exp, env, parent

    def __call__(self, *args):
        self.exp = destruct(self.parms, list(args), self.exp)
        return eval(self.exp, Env(self.parms, args, self.env))


class Procedure:
    def __init__(self, env, forms):
        self.procs = []
        self.variadic = None
        for form in forms:
            if '.' in form[0]:
                self.variadic = Proc(*form, *[env, self])
            self.procs.append(Proc(*form, *[env, self]))

            # self.procs = [Proc(*(*form, *[env])) for form in forms]

    def __call__(self, *args):
        return self.proc(*args)(*args)

    def proc(self, *args):
        for p in self.procs:
            if len(p.parms) == len(args):
                return p
        else:
            return self.variadic



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
        'car': lambda x: x[0],
        'cdr': lambda x: x[1:],
        'append': op.add,
        'list': lambda *x: list(x), 'list?': lambda x: isa(x, list),
        'null?': lambda x: x == [], 'symbol?': lambda x: isa(x, Symbol),
        'boolean?': lambda x: isa(x, bool),
        'apply': lambda proc, l: proc(*l),
        'symbol': lambda x: Symbol(x),
        'count': len,
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

    if t.isdecimal():
        return int(t)

    try:
        return float(t)
    except ValueError:
        pass

    if t.startswith('-'):
        return KeyWord(t[1:])

    if t.startswith('\'') and t.endswith('\''):
        return t[1:-1]

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
        elif x[0] == 'if':  # (if test conseq alt)
            (_, test, conseq, alt) = x
            x = (conseq if eval(test, env) else alt)
        elif x[0] == 'def':  # (define var exp)
            (_, var, exp) = x
            env[var] = eval(exp, env)
            return None
        elif x[0] == 'fn':  # (lambda (var*) exp)
            (_, exp) = x
            return Procedure(env, exp)
        elif x[0] is quote_:
            _, q = x
            return q

        else:  # (proc exp*)
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
        _d, v, body = x[0], x[1], x[2:]
        exp = expand(x[2])
        if _d is defmacro_:
            require(x, toplevel, "define-macro only allowed at top level")
            proc = eval(exp)
            require(x, callable(proc), "macro must be a procedure")
            macro_table[v] = proc  # (define-macro v proc)
            return None  # => None; add v:proc to macro_table
        return [def_, v, exp]

    elif x[0] is begin_:
        if len(x) == 1:
            return None  # (begin) => None
        else:
            return [expand(xi, toplevel) for xi in x]

    elif x[0] is fn_:  # (lambda (x) e1 e2)
        # require(x, len(x) >= 3)  # => (lambda (x) (begin e1 e2))
        body = x[1:]

        if all(isa(e, list) for e in body) and all(isa(e[0], list) for e in body):
            exp = mapv(lambda args, exp: [args, expand(exp)], *zip(*body))
        else:
            exp = [expand(body)]
        # require(x, (isa(vars, list) and all(isa(v, Symbol) for v in vars))
        #         or isa(vars, Symbol), "illegal lambda argument list")
        # exp = body[0] if len(body) == 1 else [begin_] + body
        return [fn_, exp]

    elif x[0] is quasiquote_:  # `x => expand_quasiquote(x)
        require(x, len(x) == 2)
        return expand_quasiquote(x[1])

    elif isa(x[0], Symbol) and x[0] in macro_table:
        return expand(macro_table[x[0]](*x[1:]), toplevel)  # (m arg...)

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


def test():
    pass
    # eval(parse('''[defn add
    #            [[xs] [add 0 xs]]
    #            [[acc xs]
    #             [if [= 0 [count xs]]
    #                 acc
    #                 [add [+ acc [first xs]]
    #                      [rest xs]]]]]'''))
    #
    # eval(parse('[defn foo [x] x]'))
    # eval(parse('[defn bar '
    #            '      [[] 0] '
    #            '      [[x] 1] '
    #            '      [[x y] 2] '
    #            '      [[x y z] 3]]'))
    # eval(parse("""[defn baz [[a b]] a]"""))
    # eval(parse('''[defn foo  [[a b] c] b]'''))
    # eval(parse('''[foo [list [list 1 2] 3]]'''))


def special_functions():
    eval(parse('''
    [def add +]
    
    
    '''))


if __name__ == '__main__':
    special_functions()
    if __debug__:
        test()
        repl(debug=True)
    else:

        repl()
