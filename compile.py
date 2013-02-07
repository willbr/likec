import pprint
import string
import itertools
import functools

from pf_parser import parse_tokens
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

genvar_counter = 1000

def scope(fn):
    def wrapper(*args):
        scope_stack.append({})
        r = fn(*args)
        #pp(scope_stack[-1])
        scope_stack.pop()
        return r
    return wrapper


def main ():
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)

    #pp (statements)
    #print('\n')
    compiled_statements = [compile_statement(s) for s in statements]

    print_includes()

    for fd in function_declarations:
        print (fd + ';')

    print()

    for s in compiled_statements:
        #pp(s)
        indent(s)
        print()

    for md in compiled_methods:
        indent(md)
        print()


def compile_statement(statements):
    c = compile_expression(statements)
    if isinstance(c, str):
        return c + ';'
    else:
        return c

def compile_expression(statements):
    if isinstance(statements, str):
        return expand_variable(statements)
    else:
        func_name, *args = statements
        if func_name in compile_functions.keys():
            return compile_functions[func_name](*args)
        else:
            return compile_call(func_name, *args)

@scope
def compile_def (function_name, args, return_type, *body):
    global function_headers
    compiled_body = compile_block(body)
    new_body = compile_variable_declarations() + compiled_body

    call_sig = '({}({}))'.format(
        function_name,
        compile_arguments(args))

    function_header = compile_variable(call_sig, return_type)

    if function_name != 'main':
        function_declarations.append(function_header)
        functions_declared.add(function_name)
    return [
            function_header + ' {',
            new_body,
            '}']

def compile_obj(name, *body):
    compiled_fields = []
    fields = []
    methods = []

    for exp in body:
        first, second, *tail = exp
        if first == 'def':
            methods.append(second)
            compile_obj_def(name, second, *tail)
        else:
            fields.append([first, second])
            compiled_fields.append(compile_variable(first, second) + ';')

    if 'new' not in methods:
        new_body = []

        for f, f_type in fields:
            new_body.append(['=', '.%s' % f, default_value(f_type)])

        compile_obj_def(
                name,
                'new',
                [],
                ['*', '%s_t' % name],
                *new_body
                )

    if fields:
        return [
                'typedef struct %s_s {' % name,
                compiled_fields,
                '} %s_t;' % name,
                ]
    else:
        return None

def compile_obj_def(object_name, method_name, *tail):
    global compiled_methods
    function_name = '%s__%s' % (object_name, method_name)
    compiled_methods.append(compile_def(function_name, *tail))

def compile_block(block):
    r = (compile_statement(line) for line in block)
    return [e for e in r if e]

def compile_arguments(args):
    return ', '.join(compile_variable(n, t)
            for n, t in grouper(2, args))

def compile_variable(name, typ):
    if isinstance(typ, list):
        l = [expand_object(typ[-1])]
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
    lvalue = expand_variable(lvalue)
    if in_scope(lvalue):
        rexp = compile_expression(rvalue)
        return '%s = %s' % (
                expand_deref(lvalue),
                rexp)
    else:
        declare(lvalue, rvalue)
        return None

def compile_call(name, *args):
    compiled_args = [compile_expression(a) for a in args]

    if name.find(':') >= 0:
        obj, method = name.split(':', 1)
        name = '%s__%s' % ('Int', method)
        compiled_args.insert(0, obj)

    function_calls.add(name)
    return '%s(%s)' % (name, ', '.join(compiled_args))

def compile_infix(operator, *operands):
    return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

def compile_for(a, b, c, *body):
    if b == 'in':
        c__i = genvar(c + '__i')
        c__length = genvar(c + '__length')


        declare(c__i, '0')
        declare(c__length, ['/',
            ['sizeof', c],
            ['sizeof', ['array-offset', c, '0']]])

        c_element_type = scope_stack[-1][c][1][1:]
        declare(a, default_value(c_element_type))

        init = compile_expression(['=', c__i, '0'])
        middle = 'a'
        middle = '%s < %s' % (c__i, c__length)
        step = '%s += 1' % c__i

        return [
                'for (%s) {' % '; '.join((init, middle, step)),
                ['%s = %s[%s];' % (a, c, c__i)] + compile_block(body),
                '}'
                ]
    else:
        return [
                'for ({}; {}; {}) {{'.format(a,b,c),
                compile_block(body),
                '}']

def compile_while(cond, *body):
    compile_condition = compile_expression(cond)
    return [
            'while ({}) {{'.format(compile_condition),
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

def compile_array_offset(name, offset):
    return '%s[%s]' % (name, compile_expression(offset))

def compile_return(exp):
    return 'return %s' % compile_expression(exp)

def compile_cast(typ, exp):
    return '(%s)(%s)' % (
            compile_variable('', typ),
            compile_expression(exp))

def expand_deref(v):
    deref_level = 0
    while isinstance(v, list):
        deref_level += 1
        v = v[1]
    return '*' * deref_level + v

def expand_variable(v):
    return expand_self(v)

def expand_object(v):
    def is_uppercase(c):
        return c in string.ascii_uppercase

    if is_uppercase(v[0]):
        if v[-2:] != '_t':
            v += '_t'
    return v

def expand_self(v):
    if v == '.':
        return 'self'
    elif v[0] == '.':
        return 'self->%s' % v[1:]
    return v

def genvar(x=None):
    global genvar_counter
    if x:
        r = '%s__%d' % (x, genvar_counter)
    else:
        r = 'G%d' % genvar_counter
    genvar_counter += 1
    return r

def default_value(type_list):
    t = type_list[0]
    if t == 'int':
        return '0'
    if t == '*':
        return 'NULL'
    else:
        print (t)
        raise TypeError

def indent(elem, level=0):
    if isinstance(elem, str):
        print (('    ' * level) + elem)
    elif elem == None:
        pass
    else:
        head, body, tail = elem
        indent(head, level)
        for s in body:
            indent(s, level + 1)
        indent(tail, level)

def in_scope(name):
    while isinstance(name, list) and name[0] == 'deref':
        name = name[1]

    if name == 'self':
        return True
    elif name[:6] == 'self->':
        return True
    else:
        s = scope_stack[-1]
        return name in s.keys()

def declare(lvalue, rvalue):
    #print(lvalue, rvalue)
    s = scope_stack[-1]
    initial_expression = compile_expression(rvalue)
    s[lvalue] = [initial_expression, expression_type(rvalue)]

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
        if head == 'cast':
            return tail[0]
        else:
            return expression_type(tail[0])

def print_includes():
    includes = set()
    for f in function_calls:
        library_name = lookup_library(f)
        if library_name != None:
            includes.add(library_name)

    for i in includes:
        print('#include <%s>' % i)
    print()

def lookup_library(function_name):
    for library, functions in libraries.items():
        for function in functions:
            if function == function_name:
                return library
    return None

def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)

scope_stack = []

function_declarations = []
functions_declared = set()
function_calls = set()
compiled_methods = []

libraries = {
        'stdio.h': [
            # File Operations
            'fopen',
            # Formatted Output
            'printf',
            # Formatted Input
            'fscanf',
            # Character Input and Output
            'puts',
            # Direct Input and Output
            'fread',
            'fwrite',
            # File Positioning
            'fseek',
            'ftell',
            'rewind',
            'fgetpos',
            'fsetpos',
            # Error
            'clearerr',
            'feof',
            'ferror',
            'perror',
            ],
        }

compile_functions = {
        'def': compile_def,
        'obj': compile_obj,
        '='  : compile_assignment,
        'for': compile_for,
        'while': compile_while,
        'array': compile_array,
        'return': compile_return,
        'array-offset': compile_array_offset,
        'cast': compile_cast,
        'genvar': genvar,
        'is': functools.partial(compile_infix, '=='),
        'isnt': functools.partial(compile_infix, '!='),
        }

for o in '+-*/':
    compile_functions[o] = functools.partial(compile_infix, o)

if __name__ == '__main__':
    main()

