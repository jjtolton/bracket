import bracket
import lib.lang

lib.lang.special_functions()
global_env = lib.lang.global_env


def loads(s, env=global_env):
    return lib.lang.eval(lib.lang.parse(s), env)


def brfn(s, *args, env=global_env):
    sargs = ' '.join('{}' for _ in args)
    return loads(f"[{s} {sargs}]".format(*args), env)


def br2py(namespace, out=None):
    out = out or namespace.replace('.br', '') + '.py'
    lib.lang.special_functions()
    env = bracket.add_globals(bracket.Env())
    env['require'](namespace)
    # stdnamespace = bracket.add_globals(bracket.Env())

    with open(out, 'w') as f:
        f.write('from loadbr import brfn\n')
        f.write('import bracket\n')
        f.write(f'''bracket.special_functions()\n
global_env=bracket.add_globals(bracket.Env())\n
global_env['require']('{namespace}')\n''')

        for k, v in env[namespace].items():
            # if k in stdnamespace:
            #     continue


            if callable(v):
                f.write(f'''def {bracket.munge(k)}(*args): return brfn(global_env, '{namespace}/{k}', *args)\n''')
            else:
                f.write(f'''{k}=loadbr.loads('{namespace}/{v}')\n''')


# if __name__ == '__main__':
    # print(brfn(global_env, 'add', 1, 2))
    # br2py('stdlib')
    # br2py('fib')
