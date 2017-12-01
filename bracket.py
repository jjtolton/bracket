import io
import sys

from naga import mapv

from lib.classes import Env, InPort, eof_object, Definition, Procedure, Symbol, If, Literal, Callable
from lib.global_env import add_globals
from lib.macros import defn, let
from lib.utils import to_string, isa

global_env = add_globals(Env())


def repl(prompt='$-> ', inport=InPort(sys.stdin), out=sys.stdout):
    "A prompt-read-eval-print loop."
    while True:
        try:
            if prompt:
                print(prompt, end=' ', flush=True)
            x = parse(inport)
            if x is eof_object:
                return None
            val = eval(x, global_env)
            if val is not None and out:
                output = to_string(val)
                print(f';;=> {output}')
        except Exception as e:
            print('%s: %s' % (type(e).__name__, e))
            if __debug__:
                raise e


# TODO: this more or less defeats the point of protocols, see if we can take this out before it gets out of control
special_forms = {'def': lambda _, name, body: Definition(lex(name, special_forms, macros),
                                                         lex(body, special_forms, macros)),
                 'fn': lambda _, parms, *exps: Procedure(list(map(Symbol, parms)),
                                                         [lex(e, special_forms, macros) for e in exps]),
                 'if': lambda _, cond, exp, alt=None: If(*[lex(e, special_forms, macros) for e in [cond, exp, alt]])}
macros = {'defn': lambda _, name, args, exps: defn(name, args, exps),
          'let': lambda _, forms, exps: let(forms, exps)}


def eval(x, env):
    return x.eval(env)


def atom(t):
    if isa(t, (Literal, Symbol, Procedure, Callable)):
        return t

    if t == '#t':
        return Literal(True)
    if t == '#f':
        return Literal(False)

    if t.isdecimal():
        return Literal(int(t))

    try:
        return Literal(float(t))
    except ValueError:
        pass

    if t.startswith('\'') and t.endswith('\''):
        return Literal(t[1:-1])

    return Symbol(t)


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
            return t

    t = next(inport)
    return eof_object if t is eof_object else lex(_read(t), special_forms, macros)


def parse(x):
    if isa(x, str):
        return parse(InPort(io.StringIO(x)))
    data = read(x)
    return data



eval(parse('[def add +]'), global_env)

if __name__ == '__main__':
    repl()
