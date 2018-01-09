import pprint
import sys
import traceback

from prompt_toolkit import prompt as repl_prompt
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.history import InMemoryHistory
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


def prompt_continuation(_, width):
    return [((), '#_>', ' ' * width)]


def repl(prompt='$-> ', out=sys.stdout, debug=False, env=global_env):
    "A prompt-read-eval-print loop."
    history = InMemoryHistory()
    while True:
        try:
            words = WordCompleter([*env.keys(), *macro_table.keys(), *map(str, specforms)])
            text = repl_prompt(message=prompt, completer=words, history=history, style=DocumentStyle, multiline=True,
                               get_continuation_tokens=prompt_continuation)
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
            print('%s: %s' % (type(e).__name__, '\n'.join(traceback.format_tb(e.__traceback__, limit=10))))
            if debug is True:
                raise e


if __name__ == '__main__':
    print("Welcome to [bracket]!")
    special_functions()
    repl(env=global_env)
