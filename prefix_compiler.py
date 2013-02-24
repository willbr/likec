import pprint
import string
import itertools
import functools
import collections
import re
import logging
import pdb

from prefix_parser import ast
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def scope(fn):
    def wrapper(self, *args):
        function_name, *_ = args
        logging.info('scope:enter:%s', function_name)
        self.enviroment_stack.append(collections.OrderedDict())

        r = fn(self, *args)

        #pp(self.current_scope())

        logging.info('scope:exit :%s', function_name)
        self.enviroment_stack.pop()
        return r
    return wrapper

def parse(text):
    return escape(ast(text))


def parse_range(start, end=None, step='1'):
    if end == None:
        end = start
        start = '0'
    return [start, end, step]

def compile_array(length, array_type, initial_values=None):
    raise SyntaxError('how did I get here/')
    return '{asdf %s%s}' % (length, ', '.join(initial_values))


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

def compile_address(exp):
    return '(&%s)' % compile_expression(exp)


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

def compile_sizeof(var_type):
    cv = compile_variable('', var_type)
    #print('sizeof', var_type, cv)
    return 'sizeof(%s)' % cv

def remove_quotes(msg):
    return msg[1:-1]

def is_uppercase(c):
    return c in string.ascii_uppercase

def expand_object(v):
    if is_uppercase(v[0]):
        if v[-2:] != '_t':
            v += '_t'
    return v

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

def root_variable(name):
    while isinstance(name, list):
        if name[0] in ['*', '->', 'deref', 'array_offset']:
            name = name[1]
        else:
            name = name[0]

    return name

def is_deref(rvalue):
    return isinstance(rvalue, list) and rvalue[0] == 'deref'

def is_obj_constructor(rvalue):
    return isinstance(rvalue, list) and is_obj(rvalue[0])

def is_obj(rvalue):
    return isinstance(rvalue, str) and is_uppercase(rvalue[0])

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

###########################################################


class CompiledExpression:
    def __init__(self,
            exp,
            pre=[],
            exp_type=['Int'],
            ):
        self.pre = pre
        self.exp = exp
        self.exp_type = exp_type

    def __repr__(self):
        return '<CompiledExpression pre: %s exp: "%s">' % (
                self.pre,
                self.exp,
                )

    def compile(self):
        compiled = []
        for p in self.pre:
            if isinstance(p, str):
                compiled.append(p + ';')
            else:
                compiled.extend(p)
        compiled.append(self.exp + ';')
        return compiled


class Function:
    compiled_body = None
    compiled_header = None
    is_method = False

    def __init__(self,
            name,
            arguments,
            return_type,
            ):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type

    def __repr__(self):
        return "<Function {} {} => {}>".format(
                self.name,
                self.arguments,
                self.return_type,
                )

    def compiled(self):
        return [
                self.compiled_header,
                '{',
                self.compiled_body,
                '}',
                ]


class Compiler:

    def __init__(self):
        self.input_files = []
        self.code = []

        self.global_code = []

        self.code_ast = []

        self.typedefs = {}
        self.structures = {}
        self.functions = {}
        self.objects = collections.defaultdict(dict)

        self.compiled_methods = []
        self.compiled_functions = []
        self.compiled_main_function = []

        self.macro_functions = {
                'fn_shorthand':
                self.expand_anonymous_function_shorthand,
                }

        self.function_calls = []

        self.enviroment_stack = [collections.OrderedDict()]

        self.genvar_counter = 1000

        self.keyword_compile_functions = {
                'c_def': self.compile_c_def,
                'obj': self.compile_obj,
                '='  : self.compile_assignment,
                'while': self.compile_while,
                'if': self.compile_if,
                'return': self.compile_return,
                'break': self.compile_break,
                'continue': self.compile_continue,
                '->': self.compile_indirect_component,
                'deref': self.compile_deref,
                'cast': self.compile_cast,
                'pr': self.compile_print,
                'prn': functools.partial(
                    self.compile_print,
                    end='\\n',
                    ),
                'method': self.compile_method,
                'each': self.compile_each,
                'repeat': self.compile_repeat,
                'map': self.compile_map,
                'reduce': self.compile_reduce,
                '_qm_': self.compile_ternary,
                'typedef': self.compile_typedef,
                'make_ctype': self.compile_make_ctype,
                'fn': self.compile_anonymous_function,
                'inc': functools.partial(
                    self.compile_increment,
                    pre='++',
                    ),
                'dec': functools.partial(
                    self.compile_increment,
                    pre='--',
                    ),
                'post_inc': functools.partial(
                    self.compile_increment,
                    post='++',
                    ),
                'post_dec': functools.partial(
                    self.compile_increment,
                    post='--',
                    ),
                'in': self.compile_in,
                }

        self.infix_operators = '''
        + - * /
        == !=
        += -=
        *= /=
        < >
        <= >=
        '''.split()


        for op in self.infix_operators:
            self.keyword_compile_functions[op] = functools.partial(
                    self.compile_infix,
                    op,
                    )

        self.libraries = {
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

    def compile(self):
        self.read_files()
        self.parse_code()
        self.code_ast = self.expand_macros(self.code_ast)
        self.extract_type_information()
        self.compile_statements()
        self.compile_main()
        self.write_output()

    def add_standard_code(self):
        self.add_file('standard_code.likec')

    def add_file(self, filename):
        self.input_files.append(filename)

    def read_files(self):
        for filename in self.input_files:
            with open(filename) as f:
                self.code.append(f.read())

    def parse_code(self):
        for c in self.code:
            self.code_ast.extend(parse(c))

    def extract_type_information(self):
        for statement_ast in self.code_ast:
            head = statement_ast[0]
            if head == 'obj':
                self.register_object(statement_ast)
            elif head == 'def':
                self.register_function(statement_ast)

    def register_function(self, ast):
        _, function_name, args, raw_return_type, *_ = ast
        return_type = parse_type(raw_return_type)

        if function_name in self.keyword_compile_functions:
            raise SyntaxError('Can\'t redefine keyword: %s' % function_name)
        if function_name in self.functions:
            raise SyntaxError('function redefined: %s' % function_name)
        else:
            self.functions[function_name] = Function(
                    function_name,
                    args,
                    return_type)

    def register_object(self, ast):
        _, obj_name, *body = ast

        methods = []

        for exp in body:
            head, *tail = exp
            if head == 'def':
                method_name = tail[0]
                methods.append(method_name)
                self.register_method(obj_name, tail)
            else:
                self.register_field(obj_name, exp)

        if 'new' not in methods:
            self.register_method(obj_name,
                    (
                        'new',
                        ['self', ['*', obj_name]],
                        ['*', obj_name],
                        )
                    )

        if 'die' not in methods:
            pass


    def register_method(self, object_name, exp):
        method_name, args, return_type, *body = exp
        #print(method_name, args, return_type, body)
        function_name = '%s__%s' % (object_name, method_name)
        #print('fnname', function_name)
        self.functions[function_name] = Function(
                function_name,
                args,
                return_type,
                )

    def register_field(self, object_name, exp):
        field_name, field_type = exp
        if field_name in self.objects[object_name]:
            raise SyntaxError('field redefined: %s.%s' % (object_name, field_name))
        self.objects[object_name][field_name] = field_type

    def compile_statements(self):
        for branch in self.code_ast:
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

        self.compile_c_def ('main',
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
        if isinstance(statements, str):
            return CompiledExpression(
                    exp=self.expand_variable(statements),
                    )
        else:
            func_name, *args = statements
            if func_name in self.keyword_compile_functions.keys():
                return self.keyword_compile_functions[func_name](*args)
            else:
                return self.compile_call(func_name, *args)


    @scope
    def compile_c_def(self,
            function_name,
            args,
            return_type,
            *body
            ):
        call_sig = '{}({})'.format(
            function_name,
            self.compile_def_arguments(args))
        
        #print(
                #function_name,
                #args,
                #return_type,
                #)

        result_exp = self.compile_begin(*body)
        compiled_body = result_exp.compile()
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

                f.compiled_header = function_header
                f.compiled_body = new_body

                self.functions['main'] = f
        else:
            #print('=======================')
            #pp(self.functions)
            f = self.functions[function_name]
            f.compiled_header = function_header
            f.compiled_body = new_body

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
            self.declare(n, t, 'argument')
        return ', '.join(self.compile_variable(n, t) for n, t in paired_args)

    def compile_begin(self,
            *expressions
            ):
        pre = []
        for expression in expressions:
            compiled_exp = self.compile_expression(expression)
            pre.append(compiled_exp.pre)
            pre.append(compiled_exp.exp)
        final_expression = pre.pop()
        return CompiledExpression(
                pre=pre,
                exp=final_expression,
                )

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

    def compile_constructor(self, object_name, *args):
        if object_name == 'Array':
            return self.compile_array(*args)
        else:
            return self.compile_new(object_name, *args)

    def compile_call(self, function_name, *args):
        #print(
                #function_name,
                #*args
                #)
        if is_obj(function_name):
            return self.compile_constructor(function_name, *args)
        else:
            #print(function_name, function_name in self.current_scope())
            try:
                vt = self.variable_type(function_name)
                return self.compile_method(function_name, *args)
            except KeyError:
                pass
            compiled_args = [self.compile_expression(a) for a in args]
            self.function_calls.append(function_name)
            return '%s(%s)' % (function_name, ', '.join(compiled_args))

    def write_output(self):
        self.print_includes()
        print()

        try:
            main_function = self.functions.pop('main')
        except KeyError:
            raise SyntaxError('main funciton not defined & no global code')

        functions = []
        methods = []

        for k, v in self.functions.items():
            if v.is_method:
                methods.append(v)
            else:
                functions.append(v)

        if self.typedefs:
            for k, v in self.typedefs.items():
                indent(v)
            print()

        if self.structures:
            for k, v in self.structures.items():
                indent(v)
                print()

        if functions:
            for f in functions:
                print('%s;' % f.compiled_header)
            print()

        for m in methods:
            indent(m.compiled())
            print()

        for f in functions:
            indent(f.compiled())
            print()

        indent(main_function.compiled())
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

    def compile_assignment(self, lvalue, rvalue):
        ce_r = self.compile_expression(rvalue)
        exp = '%s = %s' % (
                lvalue,
                ce_r.exp,
                )
        return CompiledExpression(
                pre=ce_r.pre,
                exp=exp,
                )

    def expression_type(self, exp):
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
            elif self.in_scope(exp):
                return self.variable_type(exp)
            else:
                #print(exp)
                return ['Int',]
        else:
            #print(exp)
            head, *tail = exp
            if head == 'CArray':
                return ['[]'] + self.expression_type(tail[0])
            elif head == 'cast':
                return tail[0]
            elif is_obj(head):
                return ['*', head]
            elif self.is_infix_operator(head):
                return self.expression_type(tail[0])
            elif head == 'sizeof':
                return ['size_t']
            elif head == '->':
                obj, field = tail
                return self.field_type(obj, field)
            elif head == 'deref':
                et = self.expression_type(tail[0])
                if et[0] == '*':
                    return [et[1]]
                elif et[0] == 'Array':
                    return ['[]', et[2]]
                else:
                    raise TypeError('tried to deref an expression that isn\'t a pointer', et)
            elif head in ['inc', 'dec', 'post_inc', 'post_dec']:
                return self.expression_type(tail[0])
            elif head == '_qm_':
                return self.expression_type(tail[1])
            elif head == 'range':
                return self.expression_type(tail[0])
            elif head == 'not':
                return self.expression_type(tail[0])
            elif head in ['map', 'filter']:
                return ['*', 'List']
            elif head in 'reduce':
                return self.expression_type(tail[0])
            elif head in 'car':
                try:
                    return tail[1]
                except IndexError:
                    pass
                return ['*', 'void']
            elif head in 'fn':
                return tail[1]
            elif head == 'in':
                return ['Int']
            elif head in 'if':
                return self.expression_type(tail[1])
            else:
                if head in self.functions:
                    return self.functions[head].return_type
                else:
                    f = self.lookup_library_function(head)
                    if f:
                        args, return_type = f
                        return return_type
                raise TypeError(exp)


    def declare(self, lvalue, var_type, var_scope='local'):
        root = root_variable(lvalue)
        if not self.in_scope(root):
            if is_deref(lvalue):
                #print(self.current_scope())
                raise SyntaxError('dereferenced before assignment: %s : %s' % (root, lvalue))
            s = self.current_scope()
            s[root] = [var_type, var_scope]


    def in_scope(self, name):
        name = root_variable(name)
        return name in self.current_scope()

    def current_scope(self):
        return self.enviroment_stack[-1]

    def compile_new(self, obj, *args):
        return self.compile_method(obj, 'new', 'NULL', *args)

    def compile_method(self, obj, method, *args):
        #print('method', obj, method, args)
        if is_obj(obj):
            return '%s__%s(%s)' % (obj, method, self.compile_arguments(*args))
        else:
            if method == 'append':
                new_args = []
                for arg in args:
                    new_args.append(self.make_constructor(arg))
            else:
                new_args = args


            obj_type = self.variable_type(obj)[1]
            return '%s__%s(%s)' % (
                    obj_type,
                    method,
                    self.compile_arguments(obj, *new_args),
                    )

    def compile_arguments(self, *args):
        new_args = []
        #print('args', args)
        for a in args:
            new_args.append(self.compile_expression(a))
            #print(a, '=>',  new_args[-1])

        return ', '.join(new_args)

    def compile_each(self, bind_expression, list_expression, *body):
        bind_name, bind_type = parse_bind(bind_expression)
        head, *tail = list_expression
        et = self.expression_type(list_expression)
        if head == 'range':
            start, end, step = parse_range(*tail)
            self.declare(bind_name, bind_type)
            init = '%s = %s' % (bind_name, start)
            cond = '%s < %s' % (
                    bind_name,
                    self.compile_expression(end),
                    )
            step = '%s += %s' % (bind_name, step)
            for_header = '; '.join((init, cond, step))
            return [
                    'for (%s) {' % for_header,
                    self.compile_block(body),
                    '}']
        elif head == 'list':
            # new list
            # assign to temp variable
            # then compile for
            raise NotImplemented
        elif et == ['*', 'List']:
            list_name = list_expression
            iterator_name = self.genvar('List', 'iterator')
            self.declare(iterator_name, ['*', 'List'])
            self.declare(bind_name, bind_type)
            init = ['=', iterator_name, list_name]
            cond = ['!=', ['->',iterator_name,'next'], 'NULL']
            step = ['=', iterator_name, ['->',iterator_name,'next']]
            bind = ['=', bind_name,
                    ['deref', ['cast', ['*'] + bind_type,
                        ['->', ['->', iterator_name, 'next'],
                            'data']]]]
            #print(init)
            #print(cond)
            #print(step)
            #print(bind)
            #pp(body)
            return self.compile_for(init, cond, step, bind, *body)
        else:
            raise NotImplemented


    def genvar(self, *args):
        x = '__'.join(args)
        if x:
            r = '%s%d' % (x, self.genvar_counter)
        else:
            r = 'G%d' % self.genvar_counter
        self.genvar_counter += 1
        return r

    def compile_for(self, a, b, c, *body):
        #print('for',a,b,c)
        if b == 'in':
            if c[0] == 'range':
                start, end, step = parse_range(*c[1:])
                self.declare(a, 'int')
                init = '%s = %s' % (a, start)
                cond = '%s < %s' % (a, self.compile_expression(end))
                step = '%s += %s' % (a, step)
                for_header = '; '.join((init, cond, step))
                return [
                        'for (%s) {' % for_header,
                        self.compile_block(body),
                        '}']
            else:
                et = self.expression_type(c)
                if et == ['*', 'List']:
                    return self.compile_for_in_list(a[0], a[1], c, *body)
                c__i = self.genvar(c + '__i')
                c__limit = self.genvar(c + '__limit')

                self.compile_assignment(c__i, '0')
                self.compile_assignment(c__limit, ['/',
                    ['sizeof', c],
                    ['sizeof', ['array-offset', c, '0']]])

                c_element_type = scope_stack[-1][c][1][1:]
                self.declare(a, self.default_value(c_element_type))

                init = self.compile_expression(['=', c__i, '0'])
                cond = '%s < %s' % (c__i, c__length)
                step = '%s += 1' % c__i

            return [
                    'for (%s) {' % '; '.join((init, cond, step)),
                    ['%s = %s[%s];' % (a, c, c__i)] +
                    self.compile_block(body),
                    '}'
                    ]
        else:
            init = self.compile_expression(a)
            cond = self.compile_expression(b)
            step = self.compile_expression(c)
            #print(init)
            #print(cond)
            #print(step)
            for_header = '; '.join((init, cond, step))
            return [
                    'for (%s) {' % for_header,
                    self.compile_block(body),
                    '}']

    def compile_indirect_component(self, *args):
        return '->'.join(self.compile_expression(a) for a in args)


    def compile_print(self,
            msg=None,
            end='',
            ):
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
                    exp, format_exp = self.split_format_block(contents)

                    if exp[0] in ['(', '[']:
                        exp_ast = parse(exp)[0]
                        et = self.expression_type(exp_ast)
                    else:
                        variable_name = escape(exp)
                        et = self.variable_type(variable_name)
                        exp_ast = variable_name

                    if et == ['*', 'String']:
                        args.append(self.compile_deref(exp_ast))
                        format_exp = '%s'
                    else:
                        args.append(self.compile_expression(exp_ast))

                    parsed.append(format_exp)
                else:
                    parsed.append(s)
            format_msg = ''.join(parsed)
        else:
            ce_msg = self.compile_expression(msg)
            et = self.expression_type(msg)
            if et == ['*', 'String']:
                args.append(compile_deref(msg))
            else:
                args.append(ce_msg)
            format_msg = '%%%s' % self.default_format_exp(ce_msg)

        args.insert(0, '"%s%s"' % (format_msg, end))
        return 'printf(%s)' % ', '.join(args)


    def field_type(self, obj, field):
        vt = self.variable_type(obj)
        if is_obj_variable(vt):
            obj_name = obj_name_from_variable_type(vt)
            return self.objects[obj_name][field]
        else:
            raise TypeError('not an object', obj)

    def expand_macros(self, tree):
        if isinstance(tree, list):
            if not tree:
                return tree

            head, *tail = tree

            if isinstance(head, list):
                pass
            elif head in self.macro_functions:
                tree = self.macro_functions[head](*tail)
                return [self.expand_macros(leaf) for leaf in tree]
            else:
                pass

            return [self.expand_macros(leaf) for leaf in tree]
        else:
            return tree

    def compile_deref(self, *args):
        if len(args) == 1:
            return '(*%s)' % self.compile_arguments(*args)
        else:
            return self.compile_array_offset(*args)

    def compile_array_offset(self, var_name, offset):
        vt = self.variable_type(var_name)
        if vt[0] == 'Array':
            # + 1 because element 0 is the length
            offset = ['+', '1', offset]
        elif vt[0] == 'CArray':
            pass
        elif vt[0] == '*':
            pass
        else:
            raise TypeError(var_name, vt)
        return '%s[%s]' % (var_name, self.compile_expression(offset))

    def compile_cast(self, typ, exp):
        #print('cast', typ, exp)
        return '(%s)(%s)' % (
                self.compile_variable('', typ),
                self.compile_expression(exp),
                )

    def make_constructor(self, arg):
        et = self.expression_type(arg)
        #print('make-construcor', arg, et)
        if isinstance(et, list) and is_obj(et[0]):
            return [et[0], arg]
        else:
            return ['make_ctype', et, arg]

    def default_value(self, type_list):
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

    def compile_code(self, new_code):
        self.code = [new_code]
        self.code_ast = []
        self.parse_code()
        self.code_ast = self.expand_macros(self.code_ast)
        self.extract_type_information()
        r = []
        for branch in self.code_ast:
            cs = self.compile_statement(branch)
            if cs:
                r.append(cs)
        return r

    def compile_map(self,
            function_exp,
            list_expression,
            ):
        function_name = self.compile_expression(function_exp)
        map_function_name = 'map_%s' % function_name
        if map_function_name not in self.functions:
            fn = self.functions[function_name]
            #print(fn)
            fn_args = fn.arguments
            element_type = fn.return_type
            number_of_arguments = len(fn_args) / 2
            if number_of_arguments != 1:
                raise TypeError('map functions can only take one argument: %s' % function_name)

            code = '''
def {mfn} (old-list (* List)) (* List)
    = new-list (List)
    each (n {et}) old-list
        new-list append ({fn} n)
    return new-list
'''.format(
        mfn=map_function_name,
        et=self.type_to_sexp(element_type),
        fn=function_name,
        )

            first_exp = self.escape(ast(code))[0]
            #print(code)
            #print(first_exp)
            #exit()
            self.register_function(first_exp)
            cs = self.compile_statement(first_exp)
            self.compiled_functions.append(cs)
        return self.compile_call(map_function_name, list_expression)

    def compile_reduce(self,
            function_exp,
            list_expression,
            initial_value=None
            ):
        function_name = self.compile_expression(function_exp)
        reduce_function_name = 'reduce_%s' % function_name
        if reduce_function_name not in self.functions:
            fn = self.functions[function_name]
            #print(fn)
            fn_args = fn.arguments
            fn_return_type = fn.return_type
            number_of_arguments = len(fn_args) / 2
            if number_of_arguments != 2:
                raise TypeError('reduce functions can only take two argument: %s' % function_name)
            if initial_value == None:
                compiled_initial_value = self.default_value(fn_return_type)
            else:
                compiled_initial_value = self.compile_expression(initial_value)
            code = '''
def {rfn} (list (* List)) {rt}
    = initial-value {civ}
    = out ({fn} initial-value (car list {rt}))
    for (node {rt}) in (cdr list)
        = out ({fn} out node)
    return out
'''.format(
                    rfn=reduce_function_name,
                    rt=self.type_to_sexp(fn_return_type),
                    fn=function_name,
                    civ=compiled_initial_value,
                    )
            first_exp = self.escape(ast(code))[0]
            #print(code)
            #print(first_exp)
            #exit()
            self.register_function(first_exp)
            cs = self.compile_statement(first_exp)
            self.compiled_functions.append(cs)
        return self.compile_call(reduce_function_name, list_expression)


    def type_to_sexp(self, t):
        if isinstance(t, list):
            if len(t) > 1:
                return '(%s)' % ' '.join(map(self.type_to_sexp, t))
            else:
                return t[0]
        else:
            return t


    def escape(self, s):
        if isinstance(s, list):
            return [self.escape(a) for a in s]
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


    def lookup_library_function(self, func_name):
        for library in self.libraries:
            try:
                return self.libraries[library][func_name]
            except KeyError:
                pass

    def compile_obj(self, name, *body):
        compiled_fields = []
        fields = []
        methods = []

        for exp in body:
            first, second, *tail = exp
            if first == 'def':
                methods.append(second)
                self.compile_obj_def(name, second, *tail)
            else:
                fields.append([first, second])
                compiled_fields.append(self.compile_variable(first, second) + ';')

        if 'new' not in methods:
            obj_typedef = '%s_t' % name
            new_body = []

            for f, f_type in fields:
                new_body.append(['=', ['->', 'self', f], self.default_value(f_type)])

            self.compile_obj_def(
                    name,
                    'new',
                    [],
                    ['*', '%s_t' % name],
                    *new_body
                    )

        if fields:
            self.typedefs[name] = 'typedef struct {0}_s {0}_t;'.format(name)

            self.structures[name] = [
                    'struct %s_s {' % name,
                    compiled_fields,
                    '};',
                    ]
        else:
            return None

    def compile_obj_def(self,
            object_name,
            method_name,
            args,
            return_type,
            *body):
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

        self.compiled_methods.append(self.compile_def(
            function_name,
            new_args,
            return_type,
            *new_body))

    def compile_ternary(self, cond, t, f='0'):
        return '(%s ? %s : %s)' % (
                self.compile_expression(cond),
                self.compile_expression(t),
                self.compile_expression(f),
                )

    def compile_while(self, cond, *body):
        compile_condition = self.compile_expression(cond)
        return [
                'while ({}) {{'.format(compile_condition),
                self.compile_block(body),
                '}']

    def compile_return(self, exp):
        return CompiledExpression(
                'return %s;' % self.compile_expression(exp)
                )

    def compile_typedef(self, name, typ):
        #print('typedef', name, typ)
        self.typedefs[name] = ('typedef %s %s;' % (
            self.compile_variable('', typ),
            name,
            ))
        return None

    def print_includes(self):
        includes = set()
        includes.add('stdbool.h')
        includes.add('stdio.h')
        for f in self.function_calls:
            library_name = self.lookup_library(f)
            if library_name != None:
                includes.add(library_name)

        for i in includes:
            print('#include <%s>' % i)

    def lookup_library(self, function_name):
        for library, functions in self.libraries.items():
            for function in functions:
                if function == function_name:
                    return library
        return None

    def default_format_exp(self, exp):
        et = self.expression_type(exp)
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

    def compile_make_ctype(self, var_type, exp):
        if isinstance(var_type, str):
            var_type = [var_type]
        fn_name = 'make_ctype_%s' % '_'.join(var_type)
        if fn_name not in self.functions:
            code = '''
def {fn} (a {vt}) (* void)
    = p (cast {pvt} (malloc (sizeof {vt})))
    = [p] a
    return p
    '''.format(
            fn=fn_name,
            vt=self.type_to_sexp(var_type),
            pvt=self.type_to_sexp(['*'] + var_type),
            )
        first_exp = self.escape(ast(code)[0])
        #print(code)
        #pp(first_exp)
        #print()
        #indent(cs)
        #exit()

        self.register_function(first_exp)
        #pp(self.functions)
        cs = self.compile_statement(first_exp)
        self.compiled_functions.append(cs)

        return self.compile_call(fn_name, exp)

    def compile_infix(self, operator, *operands):
        compiled_operands = [self.compile_expression(o) for o in operands]
        pre = [ce.pre for ce in compiled_operands]
        exps = [ce.exp for ce in compiled_operands]
        exp = '(%s)' % (' %s ' % operator).join(exps)
        return CompiledExpression(
                pre=pre,
                exp=exp,
                )

    def is_infix_operator(self, op):
        return op in self.infix_operators

    def expand_anonymous_function_shorthand(self, *statement):
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
                pass
            variable_name = self.genvar('arg')
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
        self.enviroment_stack.append(collections.OrderedDict())
        for k, v in sorted_variables.items():
            n, t = v['name'], v['type']
            self.declare(n, t, 'argument')
            args.extend((n, t))
        return_type = self.expression_type(body)
        self.enviroment_stack.pop()
        #print( ['fn', args, return_type, ['return', body]])
        #exit()
        return ['fn', args, return_type, ['return', body]]

    def split_format_block(self, block):
        #print(block)
        if block.find(':') >= 0:
            var_name, format_exp = block.split(':')
        else:
            var_name, format_exp = block, self.default_format_exp(block)
        return var_name, '%%%s' % format_exp

    def compile_anonymous_function(self, args, return_type, *body):
        #print(args, return_type, body)
        fn_name = self.genvar('anonymous_function')
        self.register_function(('fn', fn_name, args, return_type))
        cs = self.compile_def(fn_name, args, return_type, *body)
        self.compiled_functions.append(cs)
        return fn_name

    def compile_increment(self, exp, pre='', post=''):
        return '(%s%s%s)' % (pre, self.compile_expression(exp), post)

    def compile_in(self, a, b):
        b_et = self.expression_type(b)
        if b_et == ['*', 'Char']:
            chars = filter(None, re.split('(\\\\.|.)', b[1:-1]))
            tests = ('(%s == \'%s\')' % (a, c) for c in chars)
            return '(%s)' % ' || '.join(tests)
        elif b[0] == 'range':
            start, end, step = parse_range(*b[1:])
            start = self.compile_expression(start)
            end = self.compile_expression(end)
            return '(({0} <= {1}) && ({1} <= {2}))'.format(start, a, end)
        else:
            raise TypeError(a, b)

    def compile_if(self,
            predicate,
            consequent,
            alternative,
            ):

        pre = []
        return_variable = self.genvar('if')

        ce_predicate = self.compile_expression(predicate)
        ce_consequent = self.compile_expression(
                    [
                        '=',
                        return_variable,
                        consequent,
                        ]
                    )
        ce_alternative = self.compile_expression(
                    [
                        '=',
                        return_variable,
                        alternative,
                        ]
                    )

        pre.extend([
            'if (%s) {' % ce_predicate.exp,
            ce_consequent.compile(),
            '} else {',
            ce_alternative.compile(),
            '}',
            ])

        return CompiledExpression(
                pre=pre,
                exp=return_variable,
                )

    def compile_repeat(self, count, *body):
        counter_name = self.genvar('repeat')
        return self.compile_each(
                counter_name,
                ['range', count],
                *body
                )

    def compile_break(self):
        return 'break'

    def compile_continue(self):
        return 'continue'




def parse_type(type_expression):
    if isinstance(type_expression, str):
        return [type_expression]
    else:
        return type_expression

def parse_bind(exp):
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


if __name__ == '__main__':
    #logging.basicConfig(level=logging.INFO)
    script_name, input_filename = argv
    pc = Compiler()
    #pc.add_standard_code()
    pc.add_file(input_filename)
    pc.compile()
    #main()

