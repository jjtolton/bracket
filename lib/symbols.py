from naga import mapv


class Symbol(str): pass

def Sym(s, symbol_table={}):
    "Find or create unique Symbol entry for str s in symbol table."
    if s not in symbol_table:
        symbol_table[s] = Symbol(s)
    return symbol_table[s]

# @formatter:off
quote_, if_, set_, def_, fn_, begin_, defmacro_, = mapv(Sym,
"quote   if   set!  def   fn   begin   defmacro".split())

quasiquote_, unquote_, unquotesplicing_ = mapv(Sym,
"quasiquote   unquote   unquote-splicing".split())

append_, cons_, let_, cond_ = mapv(Sym,
"append cons let cond".split())

autogensym_ = Sym('autogensym')

# @formatter:on

def PyObject(x):
    return eval(x)
