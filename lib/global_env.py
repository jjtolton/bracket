import sys
from functools import reduce

import naga
from naga import conj as cons

from lib.classes import Symbol, eof_object
from lib.utils import isa, to_string


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
        # 'eval': lambda x: eval(expand(x)),
        # 'load': lambda fn: load(fn),

        # 'call/cc': callcc,
        'open-input-file': open,
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


