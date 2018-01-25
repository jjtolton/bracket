import fractions
import operator as op
from functools import lru_cache

import naga
import pickle

from lib.symbols import Symbol
from lib.utils import isa


def empty(x):
    return len(x) == 0


def add(*args):
    return 0 if empty(args) else sum(args)


def mul(*args):
    return 1 if empty(args) else reduce(op.mul, args)


def sub(*args):
    return reduce(op.sub, args) if len(args) > 1 else (0 - args[0])


class frac(fractions.Fraction):
    def __repr__(self):
        return f'{self.numerator}/{self.denominator}' if self.numerator != self.denominator else f'{self.numerator}'


def div(*args):
    return reduce(frac, args)


def gt(*args):
    return reduce(op.gt, args)


from naga import *


def lt(*args):
    return reduce(op.lt, args)


def lte(*args):
    return reduce(op.le, args)


def gte(*args):
    return reduce(op.ge, args)


def exit():
    sys.exit("Bye!")


def eq(*args):
    '=='
    return reduce(op.eq, args)


def eqq(*args):
    'is'
    return True if reduce(lambda x, y: y if x is y else False, args) is not False else False


def not_(x):
    return op.not_(x)


def neq(*args):
    return True if reduce(lambda x, y: x if x != y else y, *args) else False


count = len


def cons(a, b):
    return [a] + b


def car(x): return x[0]


def cdr(x): return x[1:]


append = naga.append


def list_(*args):
    return list(args)


def listp(x):
    return isa(x, list)


def to_list(*xs):
    if isa(xs[-1], (list, tuple)):
        xs = list(xs[:-1]) + list(xs[-1])
        return list(xs)
    elif len(xs) == 1:
        return list(xs[0])
    else:
        return list(xs)


def nullp(x):
    return x == []


def symbolp(x):
    return isa(x, Symbol)


def boolean(x):
    return isa(x, bool)


def symbol(x):
    return Symbol(x)


# range = range

def pformat(s, *args):
    return s.format(*args)


def dropv(n, x):
    return list(drop(n, x))


def false_(x):
    return x is None or x is False


def apply(f, *x, **kwargs):
    lst = x[-1]
    if isa(lst, (list, tuple, str)):
        a = list(x[:-1])
        args = a + list(lst)
    else:
        args = x
    return f(*args, **kwargs)


def kwapply(f, *args):
    *args, kwargs = args
    return f(*args, **kwargs)


def in_(a, b):
    return a in b


def memo(fn=None, max_cachesize=32):
    @decorator
    def newmemo(fn):
        def _call(*args, **kwargs):
            return fn(*args, **kwargs)

        return _call

    @decorator
    def _memo(fn):

        @lru_cache(maxsize=max_cachesize)
        def newfn(args, kwargs):
            to_args = []
            for arg in args:
                try:
                    to_args.append(pickle.loads(arg))
                except TypeError:
                    to_args.append(arg)

            _args = tuple(to_args)
            _kwargs = pickle.loads(kwargs)
            return fn(*_args, **_kwargs)

        def _call(*args, **kwargs):
            to_args = []
            for arg in args:
                try:
                    to_args.append(pickle.dumps(arg))
                except (pickle.PicklingError, TypeError):
                    to_args.append(arg)

            _args = tuple(to_args)

            _kwargs = pickle.dumps(kwargs)
            return newfn(_args, _kwargs)

        return _call

    if isinstance(fn, int):
        return memo(newmemo, max_cachesize=max_cachesize)
    else:
        return _memo(fn)









# 'eval': lambda x: eval(expand(x)),
# 'load': lambda fn: load(fn),

# 'call/cc': callcc,
# 'open-input-file': open,
# 'close-input-port': lambda p: p.file.close(),
# 'open-output-file': lambda f: open(f, 'w'),
# 'close-output-port': lambda p: p.close(),
# 'eof-object?': lambda x: x is eof_object,
# 'read-char': readchar,
# 'read': read,
# 'write': lambda x, port=sys.stdout: port.write(to_string(x)),
# 'print': lambda x: print(x),
# 'pformat': lambda s, *args: print(s.format(*args)),
# 'display': lambda x, port=sys.stdout: port.write(x if isa(x, str) else to_string(x)),
# 'newline': lambda: print(),
# '.': lambda k, v: getattr(k, v),
# 'dropv': lambda *args: list(drop(*args)),
# 'expand': lambda x: expand(x)
