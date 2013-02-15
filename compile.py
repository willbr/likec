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
    global main_lines
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    ast = escape(parse_tokens(ts))

    #pp (statements)
    #print('\n')

    compiled_functions = []

    for s in ast:
        if s[0] == 'obj':
            compile_object_fields(s)

    for s in ast:
        if s[0] in ['def', 'obj', 'typedef']:
            cs = compile_statement(s)
            if cs:
                compiled_functions.append(cs)
        else:
            main_lines.append(s)

    if not main_defined:
        if main_lines[-1][0] != 'return':
            main_lines.append(['return', '0'])

        compile_def ('main',
                ['argc', 'int', 'argv', ['CArray', '*', 'char']],
                'int',
                *main_lines)
    else:
        if main_lines:
            lines_str = ('\n'.join(str(l) for l in main_lines))
            raise SyntaxError('expressions found outside of main function:\n%s' % lines_str)


    print_includes()
    print()

    for t in typedefs:
        indent(t)

    if typedefs:
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

    indent(main_compiled)
    print()

    for s in compiled_functions:
        #pp(s)
        indent(s)
        print()

def compile_object_fields(ast):
    _, obj_name, *body = ast
    stack = body[::-1]
    fields = {}
    while stack:
        exp = stack.pop()
        if exp[0] == 'def':
            break
        field_name, field_type = exp
        fields[field_name] = field_type
    objects[obj_name] = fields

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
    global main_defined, main_compiled

    call_sig = '({}({}))'.format(
        function_name,
        compile_def_arguments(args))

    if function_name == 'main':
        if body[-1][0] != 'return':
            body = list(body)
            body.append(['return', '0'])

    compiled_body = compile_block(body)
    new_body = compile_variable_declarations() + compiled_body

    function_header = compile_variable(call_sig, return_type)

    if function_name == 'main':
        if main_defined:
            raise NameError('main is defined twice')
        else:
            main_defined = True
            main_compiled = [
                    function_header + ' {',
                    new_body,
                    '}']
    else:
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

def compile_variable(name, var_type):
    #print(name, var_type)
    if isinstance(var_type, list):
        if var_type[0] == 'cast':
            type_stack = var_type[1][::-1]
        else:
            type_stack = var_type[::-1]
        l = [expand_object(type_stack.pop(0))]
        r = [name]
        while type_stack:
            t = type_stack.pop()
            if t == '*':
                r.insert(0, t)
            elif t == 'CArray':
                r.append('[]')
            elif t == 'Array':
                # + 1 because element 0 is length
                size = int(type_stack.pop()) + 1
                r.append('[%s]' % size)
            else:
                raise TypeError(name, t)
            r.insert(0, '(')
            r.append(')')
        return '%s %s' % (''.join(l), ''.join(r))
    else:
        if name == '':
            return var_type
        else:
            return '%s %s' % (var_type, name)

def compile_assignment(lvalue, rvalue):
    #print(lvalue, rvalue)
    lines = []
    post_lines = []

    if is_obj_constructor(rvalue):
        obj_type, *args = rvalue
        if obj_type == 'List':
            rvalue = rvalue[:1]
            for arg in args:
                post_lines.append(['method', lvalue, 'append', arg])
        elif obj_type == 'Array':
            declare(lvalue, rvalue)
            rvalue = None

    if rvalue:
        #print(lvalue, rvalue)
        declare(lvalue, expression_type(rvalue))

        lines.insert(0, '%s = %s' % (
            expand_variable(lvalue),
            compile_expression(rvalue)))

        for line in post_lines:
            lines.append(compile_expression(line))

    return lines

def compile_call(name, *args):
    if is_obj(name):
        if name == 'Array':
            return compile_array(*args)
        else:
            return compile_new(name, *args)
    else:
        try:
            vt = variable_type(name)
            return compile_method(name, *args)
        except KeyError:
            compiled_args = [compile_expression(a) for a in args]
            function_calls.add(name)
            return '%s(%s)' % (name, ', '.join(compiled_args))

def compile_infix(operator, *operands):
    return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

def compile_range(start, end=None, step='1'):
    if end == None:
        end = start
        start = '0'
    return [start, end, step]

def compile_for(a, b, c, *body):
    #print('for',a,b,c)
    if b == 'in':
        if c[0] == 'range':
            start, end, step = compile_range(*c[1:])
            declare(a, 'int')
            init = '%s = %s' % (a, start)
            cond = '%s < %s' % (a, end)
            step = '%s += %s' % (a, step)
            for_header = '; '.join((init, cond, step))
            return [
                    'for (%s) {' % for_header,
                    compile_block(body),
                    '}']
        else:
            vt = variable_type(c)
            if vt == ['*', 'List']:
                return compile_for_in_list(a[0], a[1], c, *body)
            c__i = genvar(c + '__i')
            c__limit = genvar(c + '__limit')

            compile_assignment(c__i, '0')
            compile_assignment(c__limit, ['/',
                ['sizeof', c],
                ['sizeof', ['array-offset', c, '0']]])

            c_element_type = scope_stack[-1][c][1][1:]
            declare(a, default_value(c_element_type))

            init = compile_expression(['=', c__i, '0'])
            cond = '%s < %s' % (c__i, c__length)
            step = '%s += 1' % c__i

        return [
                'for (%s) {' % '; '.join((init, cond, step)),
                ['%s = %s[%s];' % (a, c, c__i)] + compile_block(body),
                '}'
                ]
    else:
        init = compile_expression(a)[0]
        cond = compile_expression(b)
        step = compile_expression(c)[0]
        #print(init)
        #print(cond)
        #print(step)
        for_header = '; '.join((init, cond, step))
        return [
                'for (%s) {' % for_header,
                compile_block(body),
                '}']

def compile_for_in_list(bind_name, bind_type, list_name, *body):
    iterator_name = genvar(list_name, 'iterator')
    declare(iterator_name, ['*', 'List'])
    declare(bind_name, bind_type)
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

def compile_array(length, array_type):
    return '{%s}' % length

def compile_variable_declarations():
    declarations = []
    s = scope_stack[-1]
    for lvalue, value in sorted(s.items()):
        var_type, var_scope = value
        #print(lvalue, var_type, var_scope)
        if var_scope == 'local':
            l = compile_variable(lvalue, var_type)
            r = default_value(var_type)
            declarations.append('%s = %s;' % (l, r))
    return declarations

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
    #print(obj, method, args)
    if is_obj(obj):
        return '%s__%s(%s)' % (obj, method, compile_arguments(*args))
    else:
        if method == 'append':
            new_args = ([expression_type(a)[0], a] for a in args)
        else:
            new_args = args

        obj_type = variable_type(obj)[1]
        return '%s__%s(%s)' % (obj_type, method,
                compile_arguments(obj, *new_args))

def compile_arguments(*args):
    return ', '.join(compile_expression(a) for a in args)

def compile_new(obj, *args):
    return compile_method(obj, 'new', 'NULL', *args)

def compile_deref(*args):
    if len(args) == 1:
        return '(*%s)' % compile_arguments(*args)
    else:
        return compile_array_offset(*args)

def compile_array_offset(var_name, offset):
    vt = variable_type(var_name)
    if vt[0] == 'Array':
        # + 1 because element 0 is the length
        offset = ['+', '1', offset]
    elif vt[0] == 'CArray':
        pass
    elif vt[0] == '*':
        pass
    else:
        raise TypeError(var_name, vt)
    return '%s[%s]' % (var_name,compile_expression(offset))

def compile_print(msg, end=''):
    et = expression_type(msg)
    args = []
    if et == ['*', 'Char']:
        msg = remove_quotes(msg)
        stack = list(filter(None, re.split('({{|{.+?}|}})', msg)[::-1]))
        parsed = []
        while stack:
            s = stack.pop()
            if s in ['{{', '}}']:
                parsed.append(s)
            elif s[0] == '{':
                var_name, format_exp = split_format_block(s[1:-1])
                args.append(var_name)
                parsed.append(format_exp)
            else:
                parsed.append(s)
        format_msg = ''.join(parsed)
    else:
        format_msg = 'magic!'

    args.insert(0, '"%s%s"' % (format_msg, end))
    return 'printf(%s)' % ', '.join(args)

def split_format_block(block):
    if block.find(':') >= 0:
        var_name, format_exp = block.split(':')
    else:
        var_name, format_exp = block, default_format_exp(block)
    return var_name, '%%%s' % format_exp

def default_format_exp(var_name):
    vt = variable_type(var_name)
    if isinstance(vt, list):
        if vt == ['*', 'Char']:
            vt = '*Char'
        else:
            vt = vt[0]

    defaults = {
            'int': '%d',
            'Int': '%d',
            '*Char': '%s',
            'Char': '%c',
            }
    try:
        return defaults[vt]
    except KeyError:
        raise TypeError('no default format expression for "%s"' % vt)

def remove_quotes(msg):
    return msg[1:-1]

def expand_variable(v):
    if isinstance(v, list):
        head, *tail = v
        if head == 'deref':
            if len(tail) == 1:
                return '(*%s)' % expand_variable(*tail)
            else:
                return compile_array_offset(*tail)
        elif head == '->':
            return '(%s)' % '->'.join(expand_variable(t) for t in tail)
        else:
            raise ValueError(v)
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
        if type_list[0] == 'cast':
            t = type_list[1][0]
        else:
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
    elif t == 'Int':
        return '0'
    elif t == 'List':
        return 'NULL'
    elif t == 'Array':
        return '{%s}' % type_list[1]
    elif t == 'Char':
        return r"'\0'"
    else:
        raise TypeError(t, type_list)

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
        if name[0] in ['*', '->', 'deref', 'array_offset']:
            name = name[1]
        else:
            name = name[0]

    return name

def variable_type(name):
    s = scope_stack[-1]
    var_type, _ = s[name]
    return var_type

def declare(lvalue, var_type, var_scope='local'):
    root = root_variable(lvalue)
    if not in_scope(root):
        if is_deref(lvalue):
            raise SyntaxError('dereferenced before assignment: %s : %s' % (root, lvalue))
        s = scope_stack[-1]
        if var_type == 'argument':
            s[root] = [var_type, var_scope]
        else:
            s[root] = [var_type, var_scope]

def is_deref(rvalue):
    return isinstance(rvalue, list) and rvalue[0] == 'deref'

def is_obj_constructor(rvalue):
    return isinstance(rvalue, list) and is_obj(rvalue[0])

def is_obj(rvalue):
    return isinstance(rvalue, str) and is_uppercase(rvalue[0])

def expression_type(exp):
    #print(exp)
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
        if head == 'CArray':
            return ['[]'] + expression_type(tail[0])
        elif head == 'cast':
            return tail[0]
        elif is_obj(head):
            return ['*', head]
        elif is_infix_operator(head):
            return expression_type(tail[0])
        elif head == 'sizeof':
            return ['size_t']
        elif head == '->':
            obj, field = tail
            return field_type(obj, field)
        elif head == 'deref':
            et = expression_type(tail[0])
            if et[0] == '*':
                return [et[1]]
            else:
                raise TypeError('tried to deref an expression that isn\'t a pointer')
        else:
            raise TypeError(exp)

def field_type(obj, field):
    vt = variable_type(obj)
    if is_obj_variable(vt):
        obj_name = obj_name_from_variable_type(vt)
        return objects[obj_name][field]
    else:
        raise TypeError('not an object', obj)

def obj_name_from_variable_type(var_type):
    if isinstance(var_type, list):
        if var_type[0] == '*' and is_obj(var_type[1]):
            return var_type[1]
    else:
        if is_obj(var_type):
            return var_type

def is_obj_variable(var_type):
    if isinstance(var_type, list):
        return var_type[0] == '*' and is_obj(var_type[1])
    else:
        is_obj(var_type)

def is_infix_operator(op):
    return op in infix_operators

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


def escape(s):
    if isinstance(s, list):
        return [escape(a) for a in s]
    else:
        if s in ['->']:
            return s
        elif s[0] in '\'"-':
            return s
        replacements = {
                '-': '_',
                '?': '_qm_',
                }
        regexp = '(%s)' % '|'.join(map(re.escape, replacements.keys()))
        new_s = []
        for a in re.split(regexp, s):
            try:
                new_s.append(replacements[a])
            except KeyError:
                new_s.append(a)
        return ''.join(new_s)


scope_stack = [collections.OrderedDict()]

typedefs = []
objects = {}
structures = []

function_declarations = []
functions_declared = set()
function_calls = set()
compiled_methods = []

main_defined = False
main_lines = []
main_compiled = None

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
        'return': compile_return,
        'array_offset': compile_array_offset,
        'cast': compile_cast,
        'typedef': compile_typedef,
        'deref': compile_deref,
        '->': compile_indirect_component,
        'method': compile_method,
        'genvar': genvar,
        'is': functools.partial(compile_infix, '=='),
        'isnt': functools.partial(compile_infix, '!='),
        'pr': compile_print,
        'prn': functools.partial(compile_print, end='\\n'),
        }

infix_operators = '''
+ - * /
== !=
+= -=
*= /=
< >
<= >=
'''.split()

for o in infix_operators:
    compile_functions[o] = functools.partial(compile_infix, o)

if __name__ == '__main__':
    main()

