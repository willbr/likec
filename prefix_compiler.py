import pprint
import string
import itertools
import functools
import collections
import re
import logging
import pdb

from prefix_parser import ast, map_tree_to_values
from prefix_tokenizer import Token
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def scope(fn):
    def wrapper(self, *args):
        function_name_token, *_ = args
        function_name = function_name_token.value
        logging.info('scope:scope>>>: %s', function_name)
        self.enviroment_stack.append(collections.OrderedDict())

        r = fn(self, *args)

        #pp(self.current_scope())

        logging.info('scope:scope<<<: %s', function_name)
        self.enviroment_stack.pop()
        return r
    return wrapper

def parse(text):
    return escape(ast(text))

def parse_type(type_expression):
    if isinstance(type_expression, Token):
        return [type_expression.value]
    else:
        return map_tree_to_values(type_expression)

def is_uppercase(c):
    return c in string.ascii_uppercase

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

def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)

def escape(s):
    if isinstance(s, list):
        return [escape(a) for a in s]
    else:
        return escape_token(s)

def escape_token(t):
    v = t.value
    if v in ['', '->']:
        pass
    elif v[0] in '\'"-':
        pass
    else:
        replacements = {
                '-': '_',
                '?': '_qm_',
                }
        regexp = '(%s)' % '|'.join(map(re.escape, replacements.keys()))
        new_v = []
        for a in re.split(regexp, v):
            try:
                new_v.append(replacements[a])
            except KeyError:
                new_v.append(a)
        v = ''.join(new_v)
    return t._replace(value=v)

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

        self.functions = {}
        self.objects = collections.defaultdict(dict)

        self.function_calls = []

        self.enviroment_stack = [collections.OrderedDict()]

        self.genvar_counter = 1000

        self.keyword_compile_functions = {
                'c_def': self.compile_c_def,
                '='  : self.compile_assignment,
                'if': self.compile_if,
                'return': self.compile_return,
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
        self.extract_type_information()
        self.compile_statements()
        self.compile_main()
        self.write_output()

    def add_standard_code(self):
        logging.info('add_standard_code')
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
            head = statement_ast[0].value
            if head == 'obj':
                self.register_object(statement_ast)
            elif head == 'def':
                self.register_function(statement_ast)

    def register_function(self, ast):
        _, func_name_token, args, raw_return_type, *_ = ast
        func_name = func_name_token.value
        return_type = parse_type(raw_return_type)

        if func_name in self.keyword_compile_functions:
            raise SyntaxError('Can\'t redefine keyword: %s' % func_name)
        if func_name in self.functions:
            raise SyntaxError('function redefined: %s' % func_name)
        else:
            self.functions[func_name] = Function(
                    func_name,
                    args,
                    return_type)

    def compile_statements(self):
        for branch in self.code_ast:
            head = branch[0].value
            if head in ['c_def', 'def', 'obj', 'typedef']:
                cs = self.compile_statement(branch)
            else:
                self.global_code.append(branch)

    def compile_main(self):
        if 'main' in self.functions and self.global_code:
            lines_str = ('\n'.join(str(l) for l in self.global_code))
            raise SyntaxError('expressions found outside of main function:\n%s' % lines_str)
        elif 'main' in self.functions:
            return
        else:
            raise Exception
            # all arguments need to be tokens
            self.compile_c_def (
                    'main',
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
        if isinstance(statements, Token):
            logging.info('compile_expression: %s', statements,)
            return CompiledExpression(
                    exp=self.expand_variable(statements.value),
                    )
        else:
            logging.info(
                    'compile_expression: %s',
                    map_tree_to_values(statements),
                    )
            token_func_name, *args = statements
            func_name = token_func_name.value
            if func_name in self.keyword_compile_functions.keys():
                return self.keyword_compile_functions[func_name](*args)
            else:
                return self.compile_call(func_name, *args)


    @scope
    def compile_c_def(self,
            function_name_token,
            args,
            return_type_exp,
            *body
            ):

        function_name = function_name_token.value
        return_type = parse_type(return_type_exp)
        logging.info('compile_c_def: %s', function_name)

        call_sig = '{}({})'.format(
            function_name,
            self.compile_def_arguments(args),
            )
        
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

    def compile_call(self,
            function_name,
            *args):
        pre = []
        logging.info('compile_call: %s', function_name)

        try:
            vt = self.variable_type(function_name)
            return self.compile_method(function_name, *args)
        except KeyError:
            pass

        self.function_calls.append(function_name)

        compiled_args = []
        for arg in args:
            ce = self.compile_expression(arg)
            compiled_args.append(ce.exp)
        exp = '%s(%s)' % (function_name, ', '.join(compiled_args))

        return CompiledExpression(
                pre=pre,
                exp=exp,
                )

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

            l = [type_stack.pop(0)]

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


    def current_scope(self):
        return self.enviroment_stack[-1]

    def genvar(self, *args):
        x = '__'.join(args)
        if x:
            r = '%s%d' % (x, self.genvar_counter)
        else:
            r = 'G%d' % self.genvar_counter
        self.genvar_counter += 1
        return r

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
        self.extract_type_information()
        r = []
        for branch in self.code_ast:
            cs = self.compile_statement(branch)
            if cs:
                r.append(cs)
        return r

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

    def compile_return(self, exp):
        return CompiledExpression(
                'return %s;' % self.compile_expression(exp)
                )

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


    def compile_infix(self, operator, *operands):
        compiled_operands = [self.compile_expression(o) for o in operands]
        print(compiled_operands)
        pre = [ce.pre for ce in compiled_operands]
        exps = [ce.exp for ce in compiled_operands]
        exp = '(%s)' % (' %s ' % operator).join(exps)
        return CompiledExpression(
                pre=pre,
                exp=exp,
                )

    def is_infix_operator(self, op):
        return op in self.infix_operators

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




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    script_name, input_filename = argv
    pc = Compiler()
    #pc.add_standard_code()
    pc.add_file(input_filename)
    pc.compile()
    #main()

