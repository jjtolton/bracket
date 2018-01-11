import sys
import traceback

from prompt_toolkit import prompt as repl_prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.layout.processors import HighlightMatchingBracketProcessor
from pygments.lexers.jvm import ClojureLexer
from pygments.style import Style
from pygments.styles.default import DefaultStyle
from pygments.token import Token

from lib.lang import global_env, special_functions, parse, eof_object, eval
# def repl(prompt='$-> ', inport=InPort(sys.stdin), out=sys.stdout, debug=False):
#     "A prompt-read-eval-print loop."
#     while True:
#         try:
#             if prompt:
#                 print(prompt, end=' ', flush=True)
#
#             x = parse(inport)
#             if x is eof_object:
#                 return
#             val = eval(x, env=global_env)
#             if val is not None and out:
#                 output = to_string(val)
#                 print(f';;=> {output}', file=out)
#             continue
#         except KeyboardInterrupt:
#             print()
#             continue
#         except Exception as e:
#             print('%s: %s' % (type(e).__name__, e))
#             if debug is True:
#                 raise e
#                 # finally:
#                 #     repl(debug=__debug__)
#
from lib.macros import macro_table
from lib.symbols import specforms
from lib.utils import to_string


class DocumentStyle(Style):
    styles = {
        Token.Menu.Completions.Completion.Current: 'bg:#00aaaa #000000',
        Token.Menu.Completions.Completion: 'bg:#008888 #ffffff',
        Token.Menu.Completions.ProgressButton: 'bg:#003333',
        Token.Menu.Completions.ProgressBar: 'bg:#00aaaa',
    }
    styles.update(DefaultStyle.styles)


class BracketLexer(ClojureLexer):
    name = 'Bracket'
    aliases = ['bracket', 'bkt']
    filenames = ['*.br']
    mimetypes = ['text/x-bracket', 'application/x-bracket']


from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Text, \
    Number, Operator, Generic, Whitespace, Punctuation, Other, Literal

BACKGROUND = "#2B2B2B"
SELECTION = "#214283"
FOREGROUND = "#A9B7C6"

RED = "#960050"
GRAY = "#808072"
JADE = "#53833D"
ORANGE = "#CB772F"
PURPLE = "#9876AA"
YELLOW = "#F1C829"
GOLD = "#FFC66D"
EMERALD = "#88BE05"
GREEN = "#6A8759"
AQUA = "#6897BB"


class DarculaStyle(Style):
    default_style = ''

    background_color = BACKGROUND
    highlight_color = SELECTION

    styles = {
        # No corresponding class for the following:
        Text: FOREGROUND,  # class:  ''
        Whitespace: "",  # class: 'w'
        Error: RED,  # class: 'err'
        Other: "",  # class 'x'

        Comment: GRAY,  # class: 'c'
        Comment.Multiline: JADE,  # class: 'cm'
        Comment.Preproc: "",  # class: 'cp'
        Comment.Single: "",  # class: 'c1'
        Comment.Special: "",  # class: 'cs'

        Keyword: ORANGE,  # class: 'k'
        Keyword.Constant: "",  # class: 'kc'
        Keyword.Declaration: "",  # class: 'kd'
        Keyword.Namespace: ORANGE,  # class: 'kn'
        Keyword.Pseudo: "",  # class: 'kp'
        Keyword.Reserved: "",  # class: 'kr'
        Keyword.Type: "",  # class: 'kt'

        Operator: FOREGROUND,  # class: 'o'
        Operator.Word: "",  # class: 'ow' - like keywords

        Punctuation: FOREGROUND,  # class: 'p'

        Name: FOREGROUND,  # class: 'n'
        Name.Attribute: "",  # class: 'na' - to be revised
        Name.Builtin: "",  # class: 'nb'
        Name.Builtin.Pseudo: "",  # class: 'bp'
        Name.Class: "",  # class: 'nc' - to be revised
        Name.Constant: ORANGE,  # class: 'no' - to be revised
        Name.Decorator: YELLOW,  # class: 'nd' - to be revised
        Name.Entity: "",  # class: 'ni'
        Name.Exception: EMERALD,  # class: 'ne'
        Name.Function: GOLD,  # class: 'nf'
        Name.Property: "",  # class: 'py'
        Name.Label: "",  # class: 'nl'
        Name.Namespace: "",  # class: 'nn' - to be revised
        Name.Other: EMERALD,  # class: 'nx'
        Name.Tag: YELLOW,  # class: 'nt' - like a keyword
        Name.Variable: "",  # class: 'nv' - to be revised
        Name.Variable.Class: "",  # class: 'vc' - to be revised
        Name.Variable.Global: "",  # class: 'vg' - to be revised
        Name.Variable.Instance: "",  # class: 'vi' - to be revised

        Number: AQUA,  # class: 'm'
        Number.Float: "",  # class: 'mf'
        Number.Hex: "",  # class: 'mh'
        Number.Integer: "",  # class: 'mi'
        Number.Integer.Long: "",  # class: 'il'
        Number.Oct: "",  # class: 'mo'

        Literal: AQUA,  # class: 'l'
        Literal.Date: GREEN,  # class: 'ld'

        String: GREEN,  # class: 's'
        String.Backtick: "",  # class: 'sb'
        String.Char: "",  # class: 'sc'
        String.Doc: "",  # class: 'sd' - like a comment
        String.Double: "",  # class: 's2'
        String.Escape: AQUA,  # class: 'se'
        String.Heredoc: "",  # class: 'sh'
        String.Interpol: "",  # class: 'si'
        String.Other: "",  # class: 'sx'
        String.Regex: "",  # class: 'sr'
        String.Single: "",  # class: 's1'
        String.Symbol: "",  # class: 'ss'

        Generic: GRAY,  # class: 'g'
        Generic.Deleted: FOREGROUND,  # class: 'gd',
        Generic.Emph: "italic",  # class: 'ge'
        Generic.Error: "",  # class: 'gr'
        Generic.Heading: "bold " + EMERALD,  # class: 'gh'
        Generic.Inserted: EMERALD,  # class: 'gi'
        Generic.Output: "",  # class: 'go'
        Generic.Prompt: "bold " + GRAY,  # class: 'gp'
        Generic.Strong: "bold",  # class: 'gs'
        Generic.Subheading: FOREGROUND,  # class: 'gu'
        Generic.Traceback: "",  # class: 'gt'
    }


def prompt_continuation(_, width):
    return [((), '#_>', ' ' * width)]


def repl(prompt='$-> ', out=sys.stdout, debug=False, env=global_env):
    "A prompt-read-eval-print loop."
    history = FileHistory('history.log')
    processor = HighlightMatchingBracketProcessor()
    while True:
        try:
            words = WordCompleter([*env.keys(), *macro_table.keys(), *map(str, specforms)])
            text = repl_prompt(message=prompt,
                               completer=words,
                               history=history,
                               style=DarculaStyle,
                               multiline=True,
                               get_continuation_tokens=prompt_continuation,
                               auto_suggest=AutoSuggestFromHistory(),
                               extra_input_processors=[processor],
                               lexer=BracketLexer)
            x = parse(text)
            if x is eof_object:
                return
            val = eval(x, env=env)
            if val is not None and out:
                output = to_string(val)
                print(f';;=> {output}', file=out)
            continue
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            sys.exit('bye!')
        except Exception as e:
            etype = type(e)
            ename = etype.__name__
            tb = '\n'.join(traceback.format_tb(e.__traceback__, limit=20))
            print(f'{etype}: {ename}\n{tb}\n\n{e}')
            if debug is True:
                raise e


if __name__ == '__main__':
    print("Welcome to [bracket]!")
    special_functions()
    repl(env=global_env)
