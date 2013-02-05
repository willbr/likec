import pprint
import itertools
import functools

from pf_parser import parse_tokens
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

scope_stack = []

def scope(fn):
    def wrapper(*args):
        scope_stack.append({
            'name': fn.__name__.split('_')[-1],
            'local': {},
            'global': {},
            })
        r = fn(*args)
        scope_stack.pop()
        return r
    return wrapper

def close_statement(fn):
    def wrapper(*args):
        return fn(*args) + ';'
    return wrapper


def main ():
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)
    #pp (statements)
    #print('\n')

    for statement in statements:
        print(compile_statement(statement))


def compile_statement(statements):
    return compile_expression(statements, ';')

def compile_expression(statements, eol=''):
    compile_functions = {
            'def': compile_def,
            '='  : compile_assignment,
            'for': compile_for,
            }

    for o in '+-*/':
        compile_functions[o] = functools.partial(compile_infix, o)

    if isinstance(statements, str):
        return statements
    else:
        func_name, *args = statements
        if func_name in compile_functions.keys():
            return compile_functions[func_name](*args)
        else:
            return compile_call(func_name, *args) + eol

@scope
def compile_def (function_name, args, return_type, *body):
    return '''{} {} ({}) {{
{}
}}'''.format(return_type,
            function_name,
            compile_arguments(args),
            compile_block(body),
            )

def compile_block(block):
    block_lines = []
    for line in block:
        block_lines.append(indent(compile_statement(line)))
    return '\n'.join(block_lines)

def compile_arguments(args):
    return ', '.join(compile_argument(n, t)
            for n, t in grouper(2, args))

def compile_argument(name, typ):
    if isinstance(typ, list):
        l = [typ[-1]]
        r = [name]
        for t in typ[:-1]:
            if t == '*':
                r.insert(0, t)
            elif t == '[]':
                r.append(t)
            else:
                raise 'unknown type'
            r.insert(0, '(')
            r.append(')')
        return '%s %s' % (''.join(l), ''.join(r))
    else:
        return '{} {}'.format(typ, name)

@close_statement
def compile_assignment(lvalue, rvalue):
    return '%s = %s' % (lvalue,
            compile_expression(rvalue))

def compile_call(name, *args):
    return '%s(%s)' % (name, ', '.join(args))

def compile_infix(operator, *operands):
    return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

@scope
def compile_for(a, b, c, *body):
    return '''for ({}; {}; {}) {{
{}
{}'''.format(a,b,c,
        compile_block(body),
        indent('}', -1))

def indent(s, offset=0):
    return ((len(scope_stack) + offset) * '    ') + s

def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)

if __name__ == '__main__':
    main()

