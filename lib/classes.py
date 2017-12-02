import re

from lib.utils import isa


class Symbol:
    def __init__(self, x):
        self.x = x

    def eval(self, env):
        return env[self.x]

    def __eq__(self, other):
        if isa(other, Symbol):
            return other.x == self.x
        else:
            return self.x == other

    def __hash__(self):
        return hash(self.x)

    def __repr__(self):
        return f"Symbol({self.x})"


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


class Procedure(SpecialForm):
    def __init__(self, parms, body):
        self.parms = parms
        self.body = body

    def __call__(self, env):
        for p, arg in zip(env.parms, env.args):
            env[p] = arg

        for exp in self.body:
            res = exp.eval(env)

        return res

    def eval(self, env=None):
        return self

    def __repr__(self):
        return f"Procedure(parms={self.parms}, body={self.body}"


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
        exps = [exp.eval(env) for exp in self.args]
        proc = self.proc.eval(env)
        if isa(proc, Procedure):

            # TODO: (maybe) scope managed here if issues
            if '.' in proc.parms:
                idx = proc.parms.index('.')
                exps = exps[:idx] + [exps[idx:]]
                parms = proc.parms[:idx] + proc.parms[idx + 1:]
                proc.parms = parms
                env = Env(parms, exps, env)
            else:
                env = Env(proc.parms, exps, env)

            return proc(env)

        else:
            return proc(*exps)


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


class Env(dict):
    def __init__(self, parms=(), args=(), outer=None):
        self.args = args
        self.parms = parms
        self.outer = outer
        super(Env, self).__init__()

    def __getitem__(self, item):
        if item in self:
            return super().__getitem__(item)
        else:
            return self.outer[item]

    def find(self, key):
        if key in self:
            return self[key]
        return self.outer.find(key)