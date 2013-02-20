import pprint
import string
import itertools
import functools
import collections
import re

from prefix_parser import ast
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

def parse(text):
    return escape(ast(text))


def expand_macros(tree):
    if isinstance(tree, list):
        if not tree:
            return tree
        head, *tail = tree
        if isinstance(head, list):
            pass
        elif head in macro_functions:
            tree = macro_functions[head](*tail)
            return [expand_macros(leaf) for leaf in tree]
        return [expand_macros(leaf) for leaf in tree]
    else:
        return tree


def main ():
    global main_lines
    input_text = open(argv[1]).read()
    file_ast = parse(input_text)

    #pp (statements)
    #print('\n')

    with open('standard_code.likec') as f:
        file_ast.extend(parse(f.read()))

    file_ast_post_macro = expand_macros(file_ast)

    for s in file_ast_post_macro:
        if s[0] == 'obj':
            compile_object_fields(s)
            compile_object_methods(s)
        elif s[0] == 'def':
            _, func_name, args, return_type, *_ = s
            if isinstance(return_type, str):
                return_type = [return_type]
            register_function(func_name, args, return_type)

    for s in file_ast_post_macro:
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

    for s in compiled_functions:
        #pp(s)
        indent(s)
        print()

    indent(main_compiled)
    print()


def register_function(function_name, args, return_type):
    if function_name in compile_functions:
        raise SyntaxError('Can\'t redefine keyword: %s' % function_name)
    if function_name in functions:
        raise SyntaxError('function redefined: %s' % function_name)
    else:
        functions[function_name] = [args, return_type]


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


def compile_object_methods(ast):
    _, obj_name, *body = ast
    stack = body[::-1]
    while stack:
        exp = stack.pop()
        if exp[0] != 'def':
            continue
        _, method_name, method_args, return_type, *body = exp
        fn_name = '%s__%s' % (obj_name, method_name)
        obj_typedef = '%s_t' % obj_name

        if method_name == 'new':
            if return_type == 'void':
                return_type = ['*', obj_typedef]

        fn_args = ['self', ['*', obj_name]] + method_args

        register_function(fn_name, fn_args, return_type)


def compile_statement(statements):
    c = compile_expression(statements)
    if isinstance(c, str):
        if c[0] + c[-1] == '()':
            return c[1:-1] + ';'
        else:
            return c + ';'
    else:
        return c

def compile_expression(statements):
    #print('exp', statements)
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

    call_sig = '{}({})'.format(
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
                    if a[-1] in '{}:':
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
    #print('compile_variable', name or 'no-name', var_type)
    if isinstance(var_type, list):
        l = []
        r = []

        if var_type[0] == 'cast':
            type_stack = var_type[1][::-1]
        elif var_type[0] == 'Array':
            type_stack = var_type[:3][::-1]
        else:
            type_stack = var_type[::-1]

        l = [expand_object(type_stack.pop(0))]

        if name:
            r.append(name)

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
                break
            else:
                raise TypeError(name, t)
            if len(r) > 1:
                r.insert(0, '(')
                r.append(')')
            #print(l, r)
        return '%s %s' % (''.join(l), ''.join(r))
    else:
        #print(name, var_type)
        if name == '':
            return expand_object(var_type)
        else:
            eo = expand_object(var_type)
            #print('cv', var_type, eo)
            return '%s %s' % (eo, name)

def compile_assignment(lvalue, rvalue):
    lines = []
    post_lines = []

    if is_obj_constructor(rvalue):
        obj_type, *args = rvalue
        if obj_type == 'List':
            rvalue = rvalue[:1]
            for arg in args:
                post_lines.append(['method', lvalue, 'append', arg])
        elif obj_type == 'Array':
            #print(lvalue, rvalue)
            declare(lvalue, rvalue)
            rvalue = None

    if rvalue:
        et = expression_type(rvalue)
        declare(lvalue, et)

        lines.insert(0, '(%s = %s)' % (
            expand_variable(lvalue),
            compile_expression(rvalue)))

        for line in post_lines:
            lines.append(compile_expression(line))

    if len(lines) == 1:
        return lines[0]
    else:
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
            pass
        compiled_args = [compile_expression(a) for a in args]
        function_calls.add(name)
        return '%s(%s)' % (name, ', '.join(compiled_args))

def compile_infix(operator, *operands):
    compiled_operands = [compile_expression(o) for o in operands]
    return '(%s)' % (' %s ' % operator).join(compiled_operands)
    #return '(%s)' % (' %s ' % operator).join(compile_expression(o) for o in operands)

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
            cond = '%s < %s' % (a, compile_expression(end))
            step = '%s += %s' % (a, step)
            for_header = '; '.join((init, cond, step))
            return [
                    'for (%s) {' % for_header,
                    compile_block(body),
                    '}']
        else:
            et = expression_type(c)
            if et == ['*', 'List']:
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
        init = compile_expression(a)
        cond = compile_expression(b)
        step = compile_expression(c)
        #print(init)
        #print(cond)
        #print(step)
        for_header = '; '.join((init, cond, step))
        return [
                'for (%s) {' % for_header,
                compile_block(body),
                '}']

def compile_for_in_list(bind_name, bind_type, list_name, *body):
    #print(bind_name, bind_type, list_name, body)
    iterator_name = genvar('List', 'iterator')
    declare(iterator_name, ['*', 'List'])
    declare(bind_name, bind_type)
    init = ['=', iterator_name, list_name]
    cond = ['isnt', ['->',iterator_name,'next'], 'NULL']
    step = ['=', iterator_name, ['->',iterator_name,'next']]
    bind = ['=', bind_name, ['deref', ['cast', ['*', bind_type], ['->', ['->', iterator_name, 'next'], 'data']]]]
    return compile_for(init, cond, step, bind, *body)

def compile_each(bind_expression, list_expression, *body):
    bind_name, bind_type = compile_bind(bind_expression)
    head, *tail = list_expression
    et = expression_type(list_expression)
    if head == 'range':
        start, end, step = compile_range(*tail)
        declare(bind_name, bind_type)
        init = '%s = %s' % (bind_name, start)
        cond = '%s < %s' % (bind_name, compile_expression(end))
        step = '%s += %s' % (bind_name, step)
        for_header = '; '.join((init, cond, step))
        return [
                'for (%s) {' % for_header,
                compile_block(body),
                '}']
    elif head == 'list':
        # new list
        # assign to temp variable
        # then compile for
        raise NotImplemented
    elif et == ['*', 'List']:
        list_name = list_expression
        iterator_name = genvar('List', 'iterator')
        declare(iterator_name, ['*', 'List'])
        declare(bind_name, bind_type)
        init = ['=', iterator_name, list_name]
        cond = ['isnt', ['->',iterator_name,'next'], 'NULL']
        step = ['=', iterator_name, ['->',iterator_name,'next']]
        bind = ['=', bind_name, ['deref', ['cast', ['*'] + bind_type, ['->', ['->', iterator_name, 'next'], 'data']]]]
        #print(init)
        #print(cond)
        #print(step)
        #print(bind)
        #pp(body)
        return compile_for(init, cond, step, bind, *body)
    else:
        raise NotImplemented

def compile_bind(exp):
    if isinstance(exp, str):
        return exp, ['Int']
    else:
        try:
            bind_name, bind_type = exp
        except ValueError:
            raise SyntaxError('Invalid bind expression')

        if isinstance(bind_type, str):
            return bind_name, [bind_type]
        else:
            return bind_name, bind_type

def compile_while(cond, *body):
    compile_condition = compile_expression(cond)
    return [
            'while ({}) {{'.format(compile_condition),
            compile_block(body),
            '}']

def compile_array(length, array_type, initial_values=None):
    raise SyntaxError('how did I get here/')
    return '{asdf %s%s}' % (length, ', '.join(initial_values))

def compile_variable_declarations():
    declarations = []
    s = scope_stack[-1]
    #pp(s)
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
    #print('cast', typ, exp)
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
            new_args = []
            for arg in args:
                new_args.append(make_constructor(arg))
        else:
            new_args = args


        obj_type = variable_type(obj)[1]
        return '%s__%s(%s)' % (obj_type, method,
                compile_arguments(obj, *new_args))

def make_constructor(arg):
    et = expression_type(arg)
    if isinstance(et, list) and len(et) == 1:
        return [et[0], arg]
    else:
        return ['make_ctype', et, arg]

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

def compile_print(msg=None, end=''):
    #print('compile_print', msg, end)
    args = []
    if msg == None:
        format_msg = ''
    elif msg[0] == '"':
        msg = remove_quotes(msg)
        stack = list(filter(None, re.split('({{|{.+?}|}})', msg)[::-1]))
        #print(stack)
        parsed = []
        while stack:
            s = stack.pop()
            if s in ['{{', '}}']:
                parsed.append(s)
            elif s[0] == '{':
                contents = s[1:-1]
                exp, format_exp = split_format_block(contents)

                if exp[0] in ['(', '[']:
                    exp_ast = parse(exp)[0]
                    et = expression_type(exp_ast)
                else:
                    variable_name = escape(exp)
                    et = variable_type(variable_name)
                    exp_ast = variable_name

                if et == ['*', 'String']:
                    args.append(compile_deref(exp_ast))
                    format_exp = '%s'
                else:
                    args.append(compile_expression(exp_ast))

                parsed.append(format_exp)
            else:
                parsed.append(s)
        format_msg = ''.join(parsed)
    else:
        ce_msg = compile_expression(msg)
        et = expression_type(msg)
        if et == ['*', 'String']:
            args.append(compile_deref(msg))
        else:
            args.append(ce_msg)
        format_msg = '%%%s' % default_format_exp(ce_msg)

    args.insert(0, '"%s%s"' % (format_msg, end))
    return 'printf(%s)' % ', '.join(args)

def compile_increment(pre='', post='', exp=''):
    declare(root_variable(exp), ['int'])
    return '(%s%s%s)' % (pre, compile_expression(exp), post)

def compile_ternary(cond, t, f='0'):
    return '(%s ? %s : %s)' % (
            compile_expression(cond),
            compile_expression(t),
            compile_expression(f),
            )

def compile_in(a, b):
    b_et = expression_type(b)
    if b_et == ['*', 'Char']:
        chars = filter(None, re.split('(\\\\.|.)', b[1:-1]))
        tests = ('(%s == \'%s\')' % (a, c) for c in chars)
        return '(%s)' % ' || '.join(tests)
    elif b[0] == 'range':
        bottom, top = b[1:]
        if isinstance(b, list):
            top = top[1]
            return '(({0} <= {1}) && ({1} <= {2}))'.format(bottom, a, top)
        else:
            return '(({0} <= {1}) && ({1} < {2}))'.format(bottom, a, top)
    else:
        raise TypeError(a, b)

def compile_cond(*args):
    lines = []
    found_else = False
    pred, *body = args[0]
    lines.extend([
        'if (%s) {' % compile_expression(pred),
        compile_block(body)])
    for test in args[1:]:
        pred, *body = test
        if pred == 'else':
            found_else = True
            lines.extend([
                '} else {',
                compile_block(body)])
        else:
            if found_else:
                raise SyntaxError('found condition after else')
            lines.extend([
                '} else if (%s) {' % compile_expression(pred),
                compile_block(body)])
    lines.append('}')
    return lines

def compile_if(pred, *body):
    return [
        'if (%s) {' % compile_expression(pred),
        compile_block(body),
        '}']

def compile_repeat(count, *body):
    counter_name = genvar('repeat')
    return compile_for(counter_name, 'in', ['range', count], *body)

def compile_switch(exp, *cases):
    lines = []
    found_default = False
    lines.extend(['switch (%s) {' % compile_expression(exp)])
    for case in cases:
        exp, *body = case
        if exp == 'default':
            found_else = True
            body.append(['break'])
            lines.extend([
                'default:',
                compile_block(body)])
        else:
            if found_default:
                raise SyntaxError('found condition after default')
            if body:
                body.append(['break'])
            lines.extend([
                'case %s:' % compile_expression(exp),
                compile_block(body)])
    lines.append('}')
    return lines

def compile_break():
    return 'break'

def compile_continue():
    return 'continue'

def compile_address(exp):
    return '(&%s)' % compile_expression(exp)

def compile_map(function_exp, list_name):
    function_name = compile_expression(function_exp)
    map_function_name = 'map_%s' % function_name
    if map_function_name not in functions:
        fn = functions[function_name]
        fn_args, fn_return_type = fn
        number_of_arguments = len(fn_args) / 2
        if number_of_arguments != 1:
            raise TypeError('map functions can only take one argument: %s' % function_name)
        arg_name, arg_type = fn_args
        element_type = arg_type
        code = '''
def {mfn} (l (* List)) (* List)
    = nl (List)
    for (n {et}) in l
        nl append ({fn} n)
    return nl
        '''.format(
                mfn=map_function_name,
                et=type_to_sexp(element_type),
                fn=function_name,
                )
        first_exp = escape(ast(code)[0])
        #pp(first_exp)
        #exit()
        cs = compile_statement(first_exp)
        compiled_functions.append(cs)
    return compile_call(map_function_name, list_name)

def compile_filter(function_exp, list_name):
    function_name = compile_expression(function_exp)
    filter_function_name = 'filter_%s' % function_name
    if filter_function_name not in functions:
        fn = functions[function_name]
        fn_args, fn_return_type = fn
        number_of_arguments = len(fn_args) / 2
        if number_of_arguments != 1:
            raise TypeError('filter functions can only take one argument: %s' % function_name)
        arg_name, arg_type = fn_args
        element_type = arg_type
        code = '''
def {ffn} (l (* List)) (* List)
    = nl (List)
    for (n {et}) in l
        if ({fn} n)
            nl append n
    return nl
        '''.format(
                ffn=filter_function_name,
                et=type_to_sexp(element_type),
                fn=function_name,
                )
        first_exp = escape(ast(code)[0])
        #pp(first_exp)
        #exit()
        cs = compile_statement(first_exp)
        compiled_functions.append(cs)
    return compile_call(filter_function_name, list_name)

def compile_reduce(function_exp, list_expression, initial_value=None):
    function_name = compile_expression(function_exp)
    reduce_function_name = 'reduce_%s' % function_name
    if reduce_function_name not in functions:
        fn = functions[function_name]
        #print(function_name, fn)
        fn_args, fn_return_type = fn
        number_of_arguments = len(fn_args) / 2
        if number_of_arguments != 2:
            raise TypeError('reduce functions can only take two argument: %s' % function_name)
        if initial_value == None:
            compiled_initial_value = default_value(fn_return_type)
        else:
            compiled_initial_value = compile_expression(initial_value)
        code = '''
def {rfn} (l (* List)) {rt}
    = iv {civ}
    = memo ({fn} iv (car l {rt}))
    for (e {rt}) in (cdr l)
        = memo ({fn} memo e)
    return memo
        '''.format(
                rfn=reduce_function_name,
                rt=type_to_sexp(fn_return_type),
                fn=function_name,
                civ=compiled_initial_value,
                )
        first_exp = escape(ast(code)[0])
        #print(code)
        #exit()
        cs = compile_statement(first_exp)
        compiled_functions.append(cs)
    return compile_call(reduce_function_name, list_expression)

def compile_car(list_exp, cast_type=None):
    if cast_type == None:
        cast_type = ['*', 'Int']
    elif isinstance(cast_type, str):
        cast_type = ['*', cast_type]
    else:
        cast_type.insert(0, '*')

    return compile_deref(['cast', cast_type, ['car_void', list_exp]])

def compile_not(exp):
    return '(!%s)' % compile_expression(exp)

def compile_anonymous_function(args, return_type, *body):
    #print(args, return_type, body)
    fn_name = genvar('anonymous_function')
    register_function(fn_name, args, return_type)
    cs = compile_def(fn_name, args, return_type, *body)
    compiled_functions.append(cs)
    return fn_name

def expand_anonymous_function_shorthand(*statement):
    def walk_statement(t):
        if isinstance(t, list):
            head, *tail = t
            if head == '$':
                return parse_variable(*tail)
            else:
                return [walk_statement(e) for e in  t]
        else:
            if t == '$':
                return parse_variable('1')
            elif t[0] == '$':
                n = t[1:]
                return parse_variable(n)
            else:
                return t

    def parse_variable(argument_number, variable_type=None):
        try:
            return local_variables[argument_number]['name']
        except KeyError:
            variable_name = genvar('arg')
            local_variables[argument_number] = {
                    'name': variable_name,
                    'type': variable_type or ['Int'],
                    }
            return variable_name

    local_variables = {}

    body = walk_statement(list(statement))
    sorted_variables = collections.OrderedDict(
            sorted(local_variables.items()))
    args = []
    scope_stack.append(collections.OrderedDict())
    for k, v in sorted_variables.items():
        n, t = v['name'], v['type']
        declare(n, t, 'argument')
        args.extend((n, t))
    return_type = expression_type(body)
    scope_stack.pop()
    #print( ['fn', args, return_type, ['return', body]])
    #exit()
    return ['fn', args, return_type, ['return', body]]

def compile_make_ctype(var_type, exp):
    if isinstance(var_type, str):
        var_type = [var_type]
    fn_name = 'make_ctype_%s' % '_'.join(var_type)
    if fn_name not in functions:
        code = '''
def {fn} (a {vt}) (* void)
    = p (cast {pvt} (malloc (sizeof {vt})))
    = [p] a
    return p
'''.format(
        fn=fn_name,
        vt=type_to_sexp(var_type),
        pvt=type_to_sexp(['*'] + var_type),
        )
    first_exp = escape(ast(code)[0])
    #pp(first_exp)
    cs = compile_statement(first_exp)
    #print()
    #indent(cs)
    #exit()
    compiled_functions.append(cs)
    return compile_call(fn_name, exp)

def compile_sizeof(var_type):
    cv = compile_variable('', var_type)
    #print('sizeof', var_type, cv)
    return 'sizeof(%s)' % cv

def type_to_sexp(t):
    if isinstance(t, list):
        if len(t) > 1:
            return '(%s)' % ' '.join(map(type_to_sexp, t))
        else:
            return t[0]
    else:
        return t

def split_format_block(block):
    #print(block)
    if block.find(':') >= 0:
        var_name, format_exp = block.split(':')
    else:
        var_name, format_exp = block, default_format_exp(block)
    return var_name, '%%%s' % format_exp

def default_format_exp(exp):
    et = expression_type(exp)
    #print('dfe', exp, et)
    if isinstance(et, list):
        if et == ['*', 'Char']:
            et = '*Char'
        elif et == ['*', 'String']:
            et = 'String'
        elif et[0] == 'Array':
            raise SyntaxError('can\'t print an Array')
        else:
            et = et[0]

    defaults = {
            'int': 'd',
            'float': 'f',
            'Int': 'd',
            '*Char': 's',
            'Char': 'c',
            'String': 's',
            '*': 'p',
            }
    try:
        return defaults[et]
    except KeyError:
        raise TypeError('no default format expression for "%s"' % et)

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
            return '%s' % '->'.join(tail)
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
    #print(type_list)
    if isinstance(type_list, list):
        if type_list[0] == 'cast':
            t = type_list[1][0]
        else:
            t = type_list[0]
    else:
        t = type_list

    if t == 'int':
        return '0'
    elif t == 'float':
        return '0.0'
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
        return '{%s}' % ', '.join([type_list[1]] + type_list[3:])
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
        s[root] = [var_type, var_scope]

def is_deref(rvalue):
    return isinstance(rvalue, list) and rvalue[0] == 'deref'

def is_obj_constructor(rvalue):
    return isinstance(rvalue, list) and is_obj(rvalue[0])

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
        elif in_scope(exp):
            return variable_type(exp)
        else:
            #print(exp)
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
            elif et[0] == 'Array':
                return ['[]', et[2]]
            else:
                raise TypeError('tried to deref an expression that isn\'t a pointer', et)
        elif head in ['inc', 'dec', 'post_inc', 'post_dec']:
            return expression_type(tail[0])
        elif head == '_qm_':
            return expression_type(tail[1])
        elif head == 'range':
            return expression_type(tail[0])
        elif head == 'not':
            return expression_type(tail[0])
        elif head in ['map', 'filter']:
            return ['*', 'List']
        elif head in 'reduce':
            return expression_type(tail[0])
        elif head in 'car':
            try:
                return tail[1]
            except IndexError:
                pass
            return ['*', 'void']
        elif head in 'fn':
            return tail[1]
        else:
            if head in functions:
                return functions[head][1]
            else:
                f = lookup_library_function(head)
                if f:
                    args, return_type = f
                    return return_type
            raise TypeError(exp)

def function_return_type(function_name):
    fn = functions[function_name]
    args, return_type = fn
    return return_type

def lookup_library_function(func_name):
    for library in libraries:
        try:
            return libraries[library][func_name]
        except KeyError:
            pass

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
        if s == '':
            return s
        elif s in ['->']:
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
macros = {}
functions = {}
structures = []

function_declarations = []
functions_declared = set()
function_calls = set()
compiled_methods = []
compiled_functions = []

main_defined = False
main_lines = []
main_compiled = None

libraries = {
        'stdio.h': {
            'getchar': [['void'], ['int']],
            },
        'stdlib.h': {
            'malloc': [['size', 'size_t'], ['*', 'void']],
            },
        'string.h': {
            'strcpy': [['s', ['*', 'char'], 'ct', ['*', 'char']], ['*', 'char']],
            'strlen': [['cs', ['*', 'char']], ['size_t']],
            },
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
        'inc': functools.partial(compile_increment, '++', ''),
        'dec': functools.partial(compile_increment, '--', ''),
        'post_inc': functools.partial(compile_increment, '', '++'),
        'post_dec': functools.partial(compile_increment, '', '--'),
        '_qm_': compile_ternary,
        'is': functools.partial(compile_infix, '=='),
        'isnt': functools.partial(compile_infix, '!='),
        'pr': compile_print,
        'prn': functools.partial(compile_print, end='\\n'),
        'in': compile_in,
        'cond': compile_cond,
        'switch': compile_switch,
        '&': compile_address,
        'address': compile_address,
        'break': compile_break,
        'continue': compile_continue,
        'if': compile_if,
        'repeat': compile_repeat,
        'map': compile_map,
        'filter': compile_filter,
        'reduce': compile_reduce,
        'car': compile_car,
        'not': compile_not,
        'fn': compile_anonymous_function,
        'make_ctype': compile_make_ctype,
        'sizeof': compile_sizeof,
        'each': compile_each,
        }

macro_functions = {
        'fn_shorthand': expand_anonymous_function_shorthand,
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

###########################################################

class Function:
    compiled_code = None

    def __init__(self,
            name,
            arguments,
            return_type,
            ):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type

class Compiler:
    input_files = []
    code = []

    global_code = []

    code_ast = []
    post_macro_ast = []

    typedefs = []

    structures = {}
    functions = {}
    objects = collections.defaultdict(dict)

    compiled_methods = []
    compiled_functions = []
    compiled_main_function = []

    function_declarations = []
    function_calls = []

    code_compile_functions = {}

    enviroment_stack = [collections.OrderedDict()]

    def __init__(self):
        #self.add_file('standard_code.likec')
        pass

    def compile(self):
        self.read_files()
        self.parse_code()
        self.expand_macros()
        self.extract_type_information()
        self.compile_statements()
        self.compile_main()
        self.write_output()

    def add_file(self, filename):
        self.input_files.append(filename)

    def read_files(self):
        for filename in self.input_files:
            with open(filename) as f:
                self.code.append(f.read())

    def parse_code(self):
        for c in self.code:
            self.code_ast.extend(parse(c))

    def expand_macros(self):
        self.post_macro_ast = expand_macros(self.code_ast)

    def extract_type_information(self):
        for statement_ast in self.post_macro_ast:
            head = statement_ast[0]
            if head == 'obj':
                self.register_object(statement_ast)
            elif head == 'def':
                self.register_function(statement_ast)

    def register_function(self, ast):
        _, function_name, args, raw_return_type, *_ = ast
        return_type = parse_type(raw_return_type)

        if function_name in self.functions:
            raise SyntaxError('Can\'t redefine keyword: %s' % function_name)
        if function_name in functions:
            raise SyntaxError('function redefined: %s' % function_name)
        else:
            self.functions[function_name] = Function(
                    function_name,
                    args,
                    return_type)

    def register_object(self, ast):
        _, obj_name, *body = ast

        for exp in body:
            if exp[0] == 'def':
                self.register_method(obj_name, exp)
            else:
                self.register_field(obj_name, exp)

    def register_method(self, object_name, exp):
        pass

    def register_field(self, object_name, exp):
        field_name, field_type = exp
        if field_name in self.objects[object_name]:
            raise SyntaxError('field redefined: %s.%s' % (object_name, field_name))
        self.objects[object_name][field_name] = field_type

    def compile_statements(self):
        for branch in self.post_macro_ast:
            if branch[0] in ['def', 'obj', 'typedef']:
                cs = self.compile_statement(branch)
                if cs:
                    self.compiled_functions.append(cs)
            else:
                self.global_code.append(branch)

    def compile_main(self):
        if 'main' in self.functions and self.global_code:
            lines_str = ('\n'.join(str(l) for l in main_lines))
            raise SyntaxError('expressions found outside of main function:\n%s' % lines_str)

        if self.global_code[-1][0] != 'return':
            self.global_code.append(['return', '0'])

        self.compile_def ('main',
                ['argc', 'int', 'argv', ['CArray', '*', 'char']],
                'int',
                *self.global_code)

    def compile_statement(self, statement):
        c = self.compile_expression(statement)
        if isinstance(c, str):
            if c[0] + c[-1] == '()':
                return c[1:-1] + ';'
            else:
                return c + ';'
        else:
            return c

    def compile_expression(self, statements):
        #print('exp', statements)
        if isinstance(statements, str):
            return self.expand_variable(statements)
        else:
            func_name, *args = statements
            if func_name in self.code_compile_functions.keys():
                return self.code_compile_functions[func_name](*args)
            else:
                return self.compile_call(func_name, *args)


    def compile_def(self,
            function_name,
            args,
            return_type,
            *body
            ):
        call_sig = '{}({})'.format(
            function_name,
            self.compile_def_arguments(args))

        if function_name == 'main':
            if body[-1][0] != 'return':
                body = list(body)
                body.append(['return', '0'])

        compiled_body = self.compile_block(body)
        new_body = self.compile_variable_declarations() + compiled_body

        function_header = self.compile_variable(call_sig, return_type)

        if function_name == 'main':
            if 'main' in self.functions:
                raise NameError('main is defined twice')
            else:
                f = Function(
                        'main',
                        args,
                        return_type,
                        )

                f.compiled_code = [
                        function_header + ' {',
                        new_body,
                        '}']

                self.functions['main'] = f
        else:
            self.function_declarations.append(function_header)
            self.functions_declared.add(function_name)
            return [
                    function_header + ' {',
                    new_body,
                    '}']

    def compile_variable_declarations(self):
        declarations = []
        s = self.enviroment_stack[-1]
        #pp(s)
        for lvalue, value in sorted(s.items()):
            var_type, var_scope = value
            #print(lvalue, var_type, var_scope)
            if var_scope == 'local':
                l = self.compile_variable(lvalue, var_type)
                r = self.default_value(var_type)
                declarations.append('%s = %s;' % (l, r))
        return declarations

    def compile_def_arguments(self, arguments):
        paired_args = [(n, t) for n, t in grouper(2, arguments)]
        for n, t in paired_args:
            declare(n, t, 'argument')
        return ', '.join(self.compile_variable(n, t) for n, t in paired_args)

    def compile_block(self, block):
        lines = []
        r = (self.compile_statement(line) for line in block)
        for e in r:
            if isinstance(e, str):
                lines.append(e)
            elif isinstance(e, list):
                for a in e: 
                    if isinstance(a, list):
                        lines.append(a)
                    else:
                        if a[-1] in '{}:':
                            lines.append(a)
                        else:
                            lines.append(a + ';')
        return lines

    def variable_type(self, name):
        s = self.enviroment_stack[-1]
        var_type, _ = s[name]
        return var_type

    def expand_variable(self, v):
        if isinstance(v, list):
            head, *tail = v
            if head == 'deref':
                if len(tail) == 1:
                    return '(*%s)' % self.expand_variable(*tail)
                else:
                    return self.compile_array_offset(*tail)
            elif head == '->':
                return '%s' % '->'.join(tail)
            else:
                raise ValueError(v)
        else:
            return v

    def compile_call(self, function_name, *args):
        if is_obj(function_name):
            if name == 'Array':
                return self.compile_array(*args)
            else:
                return self.compile_new(function_name, *args)
        else:
            try:
                vt = self.variable_type(function_name)
                return self.compile_method(function_name, *args)
            except KeyError:
                pass
            compiled_args = [self.compile_expression(a) for a in args]
            self.function_calls.append(function_name)
            return '%s(%s)' % (function_name, ', '.join(compiled_args))

    def write_output(self):
        print_includes()
        print()

        try:
            main_function = self.functions.pop('main')
        except KeyError:
            raise SyntaxError('main funciton not defined & no global code')

        if self.typedefs:
            for t in typedefs:
                indent(t)
            print()

        for s in self.structures:
            indent(s)
            print()

        for fd in self.function_declarations:
            print (fd + ';')

        print()

        for md in self.compiled_methods:
            indent(md)
            print()

        for s in self.compiled_functions:
            indent(s)
            print()

        indent(main_function.compiled_code)
        print()


    def compile_variable(self,
            name,
            var_type
            ):
        #print('compile_variable', name or 'no-name', var_type)
        if isinstance(var_type, list):
            l = []
            r = []

            if var_type[0] == 'cast':
                type_stack = var_type[1][::-1]
            elif var_type[0] == 'Array':
                type_stack = var_type[:3][::-1]
            else:
                type_stack = var_type[::-1]

            l = [expand_object(type_stack.pop(0))]

            if name:
                r.append(name)

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
                    break
                else:
                    raise TypeError(name, t)
                if len(r) > 1:
                    r.insert(0, '(')
                    r.append(')')
                #print(l, r)
            return '%s %s' % (''.join(l), ''.join(r))
        else:
            #print(name, var_type)
            if name == '':
                return expand_object(var_type)
            else:
                eo = expand_object(var_type)
                #print('cv', var_type, eo)
                return '%s %s' % (eo, name)


def parse_type(type_expression):
    if isinstance(type_expression, str):
        return [type_expression]
    else:
        return type_expression

if __name__ == '__main__':
    script_name, input_filename = argv
    pc = Compiler()
    pc.add_file(input_filename)
    pc.compile()
    #main()

