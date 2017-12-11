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


_quote, _if, _set, _define, _lambda, _begin, _definemacro, = map(Sym,
                                                                 "quote   if   set!  define   lambda   begin   define-macro".split())

_quasiquote, _unquote, _unquotesplicing = map(Sym,
                                              "quasiquote   unquote   unquote-splicing".split())

_append, _cons, _let, _cond = map(Sym, "append cons let cond".split())


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

    return Symbol(t)


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
        elif x[0] == 'if':  # (if test conseq alt)
            (_, test, conseq, alt) = x
            x = (conseq if eval(test, env) else alt)
        elif x[0] == 'def':  # (define var exp)
            (_, var, exp) = x
            env[var] = eval(exp, env)
            return None
        elif x[0] == 'fn':  # (lambda (var*) exp)
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


def require(x, predicate, msg="wrong length"):
    "Signal a syntax error if predicate is false."
    if not predicate: raise SyntaxError(to_string(x) + ': ' + msg)


def expand(x, toplevel=False):
    "Walk tree of x, making optimizations/fixes, and signaling SyntaxError."
    require(x, x != [])  # () => Error
    if not isa(x, list):  # constant => unchanged
        return x
    elif x[0] is _quote:  # (quote exp)
        require(x, len(x) == 2)
        return x
    elif x[0] is _if:
        if len(x) == 3: x = x + [None]  # (if t c) => (if t c None)
        require(x, len(x) == 4)
        return map(expand, x)
    elif x[0] is _set:
        require(x, len(x) == 3)
        var = x[1]  # (set! non-var exp) => Error
        require(x, isa(var, Symbol), "can set! only a symbol")
        return [_set, var, expand(x[2])]
    elif x[0] is _define or x[0] is _definemacro:
        require(x, len(x) >= 3)
        _def, v, body = x[0], x[1], x[2:]
        if isa(v, list) and v:  # (define (f args) body)
            f, args = v[0], v[1:]  # => (define f (lambda (args) body))
            return expand([_def, f, [_lambda, args] + body])
        else:
            require(x, len(x) == 3)  # (define non-var/list exp) => Error
            require(x, isa(v, Symbol), "can define only a symbol")
            exp = expand(x[2])
            if _def is _definemacro:
                require(x, toplevel, "define-macro only allowed at top level")
                proc = eval(exp)
                require(x, callable(proc), "macro must be a procedure")
                macro_table[v] = proc  # (define-macro v proc)
                return None  # => None; add v:proc to macro_table
            return [_define, v, exp]
    elif x[0] is _begin:
        if len(x) == 1:
            return None  # (begin) => None
        else:
            return [expand(xi, toplevel) for xi in x]
    elif x[0] is _lambda:  # (lambda (x) e1 e2)
        require(x, len(x) >= 3)  # => (lambda (x) (begin e1 e2))
        vars, body = x[1], x[2:]
        require(x, (isa(vars, list) and all(isa(v, Symbol) for v in vars))
                or isa(vars, Symbol), "illegal lambda argument list")
        exp = body[0] if len(body) == 1 else [_begin] + body
        return [_lambda, vars, expand(exp)]
    elif x[0] is _quasiquote:  # `x => expand_quasiquote(x)
        require(x, len(x) == 2)
        return expand_quasiquote(x[1])
    elif isa(x[0], Symbol) and x[0] in macro_table:
        return expand(macro_table[x[0]](*x[1:]), toplevel)  # (m arg...)
    else:  # => macroexpand if m isa macro
        return mapv(expand, x)  # (f arg...) => expand each


macro_table = {Sym('defn'): defn,
               Sym('let'): let}  ## More macros can go here


def is_pair(x): return x != [] and isa(x, list)


def expand_quasiquote(x):
    """Expand `x => 'x; `,x => x; `(,@x y) => (append x y) """
    if not is_pair(x):
        return [_quote, x]
    require(x, x[0] is not _unquotesplicing, "can't splice here")
    if x[0] is _unquote:
        require(x, len(x) == 2)
        return x[1]
    elif is_pair(x[0]) and x[0][0] is _unquotesplicing:
        require(x[0], len(x[0]) == 2)
        return [_append, x[0][1], expand_quasiquote(x[1:])]
    else:
        return [_cons, expand_quasiquote(x[0]), expand_quasiquote(x[1:])]


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
