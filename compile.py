import pprint
import itertools
import functools

from pf_parser import parse_tokens
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def scope(fn):
    def wrapper(*args):
        scope_stack.append({})
        r = fn(*args)
        scope_stack.pop()
        return r
    return wrapper


def main ():
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)

    #pp (statements)
    #print('\n')

    for statement in statements:
        s = compile_statement(statement)
        #pp(s)
        indent(s)


def compile_statement(statements):
    c = compile_expression(statements)
    if isinstance(c, str):
        return c + ';'
    else:
        return c

def compile_expression(statements):
    if isinstance(statements, str):
        return statements
    else:
        func_name, *args = statements
        if func_name in compile_functions.keys():
            return compile_functions[func_name](*args)
        else:
            return compile_call(func_name, *args)

@scope
def compile_def (function_name, args, return_type, *body):
    compiled_body = compile_block(body)
    new_body = compile_variable_declarations() + compiled_body
    return [
            '{} {} ({}) {{'.format(
                return_type,
                function_name,
                compile_arguments(args)),
            new_body,
            '}']

def compile_block(block):
    r = (compile_statement(line) for line in block)
    return [e for e in r if e]

def compile_arguments(args):
    return ', '.join(compile_variable(n, t)
            for n, t in grouper(2, args))

def compile_variable(name, typ):
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

def compile_assignment(lvalue, rvalue):
    if in_scope(lvalue):
        rexp = compile_expression(rvalue)
        return '%s = %s' % (lvalue, rexp)
    else:
        declare(lvalue, rvalue)
        return None

def compile_call(name, *args):
    return '%s(%s)' % (name, ', '.join(args))

def compile_infix(operator, *operands):
    return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

def compile_for(a, b, c, *body):
    return [
            'for ({}; {}; {}) {{'.format(a,b,c),
            compile_block(body),
            '}']

def compile_array(*args):
    return '{' + ', '.join(args) + '}'

def compile_variable_declarations():
    declarations = []
    s = scope_stack[-1]
    for lvalue, value in sorted(s.items()):
        rvalue, typ = value
        declarations.append('%s = %s;' % (compile_variable(lvalue, typ), rvalue))
    return declarations

def indent(elem, level=0):
    if isinstance(elem, str):
        print (('    ' * level) + elem)
    else:
        head, body, tail = elem
        indent(head, level)
        for s in body:
            indent(s, level + 1)
        indent(tail, level)

def in_scope(name):
    s = scope_stack[-1]
    return name in s.keys()

def declare(lvalue, rvalue):
    s = scope_stack[-1]
    rexp = compile_expression(rvalue)
    s[lvalue] = [rexp, expression_type(rvalue)]

def expression_type(exp):
    if isinstance(exp, str):
        c = exp[0]
        if c == '"':
            return ['*', 'char']
        elif c == '\'':
            return ['char',]
        else:
            return ['int',]
    else:
        head, *tail = exp
        if head == 'array':
            return ['[]'] + expression_type(tail[0])
        else:
            return expression_type(tail[0])

def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)

scope_stack = []

compile_functions = {
        'def': compile_def,
        '='  : compile_assignment,
        'for': compile_for,
        'array': compile_array,
        }

for o in '+-*/':
    compile_functions[o] = functools.partial(compile_infix, o)

if __name__ == '__main__':
    main()

