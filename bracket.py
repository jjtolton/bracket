import sys

from lib.lang import eof_object, parse, InPort, global_env, eval, special_functions
from lib.utils import to_string


def repl(prompt='$-> ', inport=InPort(sys.stdin), out=sys.stdout, debug=False):
    "A prompt-read-eval-print loop."
    while True:
        try:
            if prompt:
                print(prompt, end=' ', flush=True)

            x = parse(inport)
            if x is eof_object:
                return
            val = eval(x, env=global_env)
            if val is not None and out:
                output = to_string(val)
                print(f';;=> {output}', file=out)
            continue
        except KeyboardInterrupt:
            print()
            continue
        except Exception as e:
            print('%s: %s' % (type(e).__name__, e))
            if debug is True:
                raise e
                # finally:
                #     repl(debug=__debug__)


if __name__ == '__main__':
    print("Welcome to [bracket]!")
    special_functions()
    repl(debug=__debug__)
