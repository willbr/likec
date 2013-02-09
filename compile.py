import pprint
import string
import itertools
import functools
import collections
import re

from pf_parser import parse_tokens
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

genvar_counter = 1000

def scope(fn):
    def wrapper(*args):
        scope_stack.append(collections.OrderedDict())
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

    for t in typedefs:
        indent(t)

    print()

    for s in structures:
        indent(s)
        print()

    for fd in function_declarations:
        print (fd + ';')

    print()


    for md in compiled_methods:
        indent(md)
        print()

    for s in compiled_statements:
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

    call_sig = '({}({}))'.format(
        function_name,
        compile_def_arguments(args))

    compiled_body = compile_block(body)
    new_body = compile_variable_declarations() + compiled_body

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
        obj_typedef = '%s_t' % name
        new_body = []

        for f, f_type in fields:
            new_body.append(['=', ['->', 'self', f], default_value(f_type)])

        compile_obj_def(
                name,
                'new',
                [],
                ['*', '%s_t' % name],
                *new_body
                )

    if fields:
        typedefs.append('typedef struct {0}_s {0}_t;'.format(name))

        structures.append([
                'struct %s_s {' % name,
                compiled_fields,
                '};',
                ])
    else:
        return None

def compile_obj_def(
        object_name,
        method_name,
        args,
        return_type,
        *body):
    global compiled_methods
    function_name = '%s__%s' % (object_name, method_name)
    obj_typedef = '%s_t' % object_name

    if method_name == 'new':
        if return_type == 'void':
            return_type = ['*', obj_typedef]

        new_body = []
        new_body.append(['=', 'self', ['cast', ['*', obj_typedef], ['malloc', ['sizeof', obj_typedef]]]])
        new_body.extend(body)
        new_body.append(['return', 'self'])
    else:
        new_body = body

    new_args = ['self', ['*', object_name]] + args


    compiled_methods.append(compile_def(
        function_name,
        new_args,
        return_type,
        *new_body))

def compile_block(block):
    lines = []
    r = (compile_statement(line) for line in block)
    for e in r:
        if isinstance(e, str):
            lines.append(e)
        elif isinstance(e, list):
            for a in e: 
                if isinstance(a, list):
                    lines.append(a)
                else:
                    if a[-1] in '{}':
                        lines.append(a)
                    else:
                        lines.append(a + ';')
    return lines

def compile_def_arguments(args):
    paired_args = [(n, t) for n, t in grouper(2, args)]
    for n, t in paired_args:
        declare(n, t, 'argument')
    return ', '.join(compile_variable(n, t) for n, t in paired_args)

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
        if name == '':
            return typ
        else:
            return '%s %s' % (typ, name)

def compile_assignment(lvalue, rvalue):
    lines = []
    post_lines = []

    if is_obj_constructor(rvalue):
        new, obj_type, *args = rvalue
        if obj_type == 'List':
            rvalue = rvalue[:2]
            for arg in args:
                post_lines.append(['method', lvalue, 'append', arg])

    if in_scope(lvalue):
        rexp = compile_expression(rvalue)
        lines.insert(0, '%s = %s' % (expand_variable(lvalue), rexp))
    else:
        declare(root_variable(lvalue), rvalue)

    for line in post_lines:
        lines.append(compile_expression(line))

    return lines

def compile_call(name, *args):
    compiled_args = [compile_expression(a) for a in args]
    function_calls.add(name)
    return '%s(%s)' % (name, ', '.join(compiled_args))

def compile_infix(operator, *operands):
    return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

def compile_for(a, b, c, *body):
    if b == 'in':
        vt = variable_type(c)
        if vt == 'List':
            return compile_for_in_list(a[0], a[1], c, *body)
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
        init = compile_expression(a)[0]
        cond = compile_expression(b)
        step = compile_expression(c)[0]
        for_header = '; '.join((init, cond, step))
        return [
                init,
                'for (%s) {' % for_header,
                compile_block(body),
                '}']

def compile_for_in_list(bind_name, bind_type, list_name, *body):
    iterator_name = genvar(list_name, 'iterator')
    declare(iterator_name, ['cast', ['*', 'List'], 'NULL'])
    declare(bind_name, default_value(bind_type))
    init = ['=', iterator_name, list_name]
    cond = ['isnt', ['->',iterator_name,'next'], 'NULL']
    step = ['=', iterator_name, ['->',iterator_name,'next']]
    bind = ['=', bind_name, ['deref', ['cast', ['*', bind_type], ['->', ['->', iterator_name, 'next'], 'data']]]]
    return compile_for(init, cond, step, bind, *body)

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
        rvalue, typ, var_type = value
        if var_type == 'local':
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

def compile_typedef(name, typ):
    typedefs.append('typedef %s %s;' % (compile_variable('', typ), name))
    return None

def compile_indirect_component(*args):
    return '->'.join(compile_expression(a) for a in args)

def compile_method(obj, method, *args):
    if is_obj(obj):
        return '%s__%s(%s)' % (obj, method, compile_arguments(*args))
    else:
        if method == 'append':
            new_args = (['new', expression_type(a)[0], a] for a in args)
        else:
            new_args = args
        return '%s__%s(%s)' % (variable_type(obj), method,
                compile_arguments(obj, *new_args))

def compile_arguments(*args):
    return ', '.join(compile_expression(a) for a in args)

def compile_new(obj, *args):
    return compile_method(obj, 'new', 'NULL', *args)

def compile_deref(*args):
    return '(*%s)' % compile_arguments(*args)

def expand_variable(v):
    if isinstance(v, list):
        head, *tail = v
        if head == 'deref':
            return '(*%s)' % expand_variable(*tail)
        elif head == '->':
            return '(%s)' % '->'.join(expand_variable(t) for t in tail)
        else:
            raise ValueError
    else:
        return v

def is_uppercase(c):
    return c in string.ascii_uppercase

def expand_object(v):
    if is_uppercase(v[0]):
        if v[-2:] != '_t':
            v += '_t'
    return v

def genvar(*args):
    global genvar_counter
    x = '__'.join(args)
    if x:
        r = '%s%d' % (x, genvar_counter)
    else:
        r = 'G%d' % genvar_counter
    genvar_counter += 1
    return r

def default_value(type_list):
    if isinstance(type_list, list):
        t = type_list[0]
    else:
        t = type_list

    if t == 'int':
        return '0'
    elif t == '*':
        return 'NULL'
    elif t == '[]':
        return '{}'
    elif t == 'size_t':
        return '0'
    else:
        print (t)
        raise TypeError

#def indent(elem, level=0):
    #if isinstance(elem, str):
        #print (('    ' * level) + elem)
    #elif elem == None:
        #pass
    #else:
        #head, body, tail = elem
        #indent(head, level)
        #for s in body:
            #indent(s, level + 1)
        #indent(tail, level)

def indent(elem, level=0):
    if isinstance(elem, str):
        print (('    ' * level) + elem)
    elif elem == None:
        pass
    else:
        for e in elem:
            if isinstance(e, list):
                indent(e, level + 1)
            else:
                indent(e, level)

def in_scope(name):
    name = root_variable(name)
    s = scope_stack[-1]
    return name in s.keys()

def root_variable(name):
    while isinstance(name, list):
        name = name[1]
    return name

def variable_type(name):
    s = scope_stack[-1]
    _, typ, _ = s[name]
    return typ[-1]

def declare(lvalue, rvalue, var_type='local'):
    #print(lvalue, rvalue)
    s = scope_stack[-1]
    if var_type == 'argument':
        s[lvalue] = [None, rvalue, var_type]
    else:
        initial_expression = compile_expression(rvalue)
        s[lvalue] = [initial_expression, expression_type(rvalue), var_type]

def is_obj_constructor(rvalue):
    return isinstance(rvalue, list) and rvalue[0] == 'new'

def is_obj(rvalue):
    return isinstance(rvalue, str) and is_uppercase(rvalue[0])

def expression_type(exp):
    if isinstance(exp, str):
        if exp in ['true', 'false']:
            return ['Bool']
        elif exp == 'NULL':
            return ['*']

        c = exp[0]
        if c == '"':
            return ['*', 'Char']
        elif c == '\'':
            return ['Char']
        elif c == '{':
            return ['[]']
        else:
            return ['Int',]
    else:
        #print(exp)
        head, *tail = exp
        if head == 'array':
            return ['[]'] + expression_type(tail[0])
        elif head == 'cast':
            return tail[0]
        elif head == 'new':
            return ['*', tail[0]]
        elif is_uppercase(head[0]):
            return ['*', head]
        else:
            #print(exp)
            raise TypeError

def print_includes():
    includes = set()
    includes.add('stdbool.h')
    includes.add('stdio.h')
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

scope_stack = [collections.OrderedDict()]

typedefs = []
structures = []
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
        'string.h': [
            'strcpy',
            'strncpy',
            'strcmp',
            'strncmp',
            'strchr',
            'strrchr',
            'strspn',
            'strcspn',
            'strpbrk',
            'strstr',
            'strlen',
            'strerror',
            'strtok',
            'memcpy',
            'memmove',
            'memcmp',
            'memchr',
            'memset',
            ],
        'stdlib.h': [
            'atof',
            'atoi',
            'atol',
            'strtod',
            'strtol',
            'rand',
            'srand',
            'calloc',
            'malloc',
            'realloc',
            'free',
            'abort',
            'exit',
            'atexit',
            'system',
            'getenv',
            'bsearch',
            'qsort',
            'abs',
            'labs',
            'div',
            'ldiv',
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
        'typedef': compile_typedef,
        'deref': compile_deref,
        '->': compile_indirect_component,
        'method': compile_method,
        'new': compile_new,
        'genvar': genvar,
        'is': functools.partial(compile_infix, '=='),
        'isnt': functools.partial(compile_infix, '!='),
        }

for o in '+-*/':
    compile_functions[o] = functools.partial(compile_infix, o)

if __name__ == '__main__':
    main()

