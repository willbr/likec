import pprint
import string
import itertools
import functools
import collections
import re
import logging
import pdb

from prefix_parser import ast, map_tree_to_values, map_tree
from prefix_tokenizer import Token
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def scope(fn):
    def wrapper(self, *args, **kwargs):
        function_name_token, *_ = args
        function_name = function_name_token.value
        self.enviroment_stack.append(collections.OrderedDict())
        r = fn(self, *args, **kwargs)
        self.enviroment_stack.pop()
        return r
    return wrapper

log_indent = 0
def log_compile(fn):
    def wrapper(self, *args, **kwargs):
        global log_indent
        #args_string = str(args)
        indent_string = '-' * log_indent
        pretty_args = []
        for a in args:
            if isinstance(a, str):
                pretty_args.append(a)
            else:
                pretty_args.append(str(map_tree_to_values(a)))
        args_string = ', '.join(pretty_args),
        logging.info(
                '%s>:%s: %s',
                indent_string,
                fn.__name__,
                args_string,
                )
        log_indent += 1
        r = fn(self, *args, **kwargs)
        log_indent -= 1
        logging.info(
                '<%s:%s: %s',
                indent_string,
                fn.__name__,
                r,
                )
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

#def indent(elem, level=0):
    #if isinstance(elem, str):
        #print (('    ' * level) + elem)
    #elif elem == None:
        #pass
    #else:
        #for e in elem:
            #if isinstance(e, list):
                #indent(e, level + 1)
            #else:
                #indent(e, level)

def indent(tree):
    for elem in indent_code(tree):
        print(elem)

def indent_code(tree, level=-1):
    if isinstance(tree, str):
        yield (('    ' * level) + tree)
    elif isinstance(tree, list):
        for branch in tree:
            for leaf in indent_code(branch, level + 1):
                yield leaf

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
        s = ['CompiledExpression']
        if self.pre:
            s.append('pre: %s' % str(self.pre))
        s.append('exp: {%s}' % str(self.exp))
        return '<%s>' % ' '.join(s)

    def compile(self):
        compiled = []
        for p in self.pre:
            compiled.append(p)
        compiled.append(self.exp + ';')
        return compiled


class Function:
    def __init__(self,
            name,
            arguments,
            return_type,
            ):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type

        self.compiled = False
        self.compiled_body = None
        self.compiled_header = None
        self.is_method = False

    def __repr__(self):
        return "<Function {} ( {} ) => {}, compiled:{}>".format(
                self.name,
                self.arguments,
                self.return_type,
                self.compiled,
                )

    def compile(self):
        return [
                self.compiled_header,
                '{',
                self.compiled_body,
                '}',
                ]


class Variable:

    def __init__(self,
            name,
            typ,
            scope,
            macro_code=None,
            ):
        self.name = name
        self.type = typ
        self.scope = scope
        self.macro_code = macro_code

    def __repr__(self):
        s = [self.__class__.__name__]
        s.append(str(self.name))
        s.append(str(self.type))
        s.append(str(self.scope))
        return '<%s>' % ' '.join(s)

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
                '$': self.compile_identity,
                'macro': self.compile_macro_definition,
                'def': self.compile_def,
                'set'  : self.compile_assignment,
                'if': self.compile_if,
                'cond': self.compile_cond,
                'begin': self.compile_begin,
                'while': self.compile_while,
                'for': self.compile_for,
                'each': self.compile_each,
                'case': self.compile_case,
                'in': self.compile_in,
                'not': rewrite_match_id('!', self.compile_prefix),
                'and': rewrite_match_id('&&', self.compile_infix),
                'or': rewrite_match_id('||', self.compile_infix),
                '=': rewrite_match_id('==', self.compile_comparison),
                '+': self.compile_addition_or_substitution,
                '-': self.compile_addition_or_substitution,
                'inc': rewrite_match_id('++', self.compile_prefix),
                'dec': rewrite_match_id('--', self.compile_prefix),
                'post_inc': rewrite_match_id('++', self.compile_suffix),
                'post_dec': rewrite_match_id('--', self.compile_suffix),
                }

        self.arithmetic_operators = '''
        * /
        %
        '''.split()

        self.compound_assignment_operators = '''
        += -=
        *= /=
        &= |=
        ^=
        <<= >>=
        '''.split()

        self.comparison_operators = '''
        == !=
        < >
        <= >=
        '''.split()



        for op in self.arithmetic_operators:
            self.keyword_compile_functions[op] = self.compile_infix

        for op in self.compound_assignment_operators:
            self.keyword_compile_functions[op] = self.compile_infix_two_arguments

        for op in self.comparison_operators:
            self.keyword_compile_functions[op] = self.compile_comparison

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

    def add_standard_code(self):
        self.add_file('standard_code.likec')

    def add_file(self, filename):
        self.input_files.append(filename)

    def add_code(self, text):
        self.code.append(text)

    def read_files(self):
        for filename in self.input_files:
            logging.info('read_files: %s', filename)
            with open(filename) as f:
                self.add_code(f.read())

    def parse_code(self):
        for c in self.code:
            self.code_ast.extend(parse(c))

    def extract_type_information(self):
        for statement_ast in self.code_ast:
            head = statement_ast[0].value
            if head == 'def':
                self.register_function(statement_ast)
            elif head == 'macro':
                self.compile_macro_definition(*statement_ast)

    def register_function(self, ast):
        _, func_name_token, args, raw_return_type, *_ = ast
        func_name = func_name_token.value
        return_type = parse_type(raw_return_type)
        logging.info('register_function: %s', func_name)

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
        r = []
        for branch in self.code_ast:
            head = branch[0].value
            if head in ['def', 'obj', 'typedef']:
                cs = self.compile_statement(branch)
                r.append(cs)
            else:
                self.global_code.append(branch)
        return r

    def compile_main(self):
        if 'main' in self.functions and self.global_code:
            lines_str = ('\n'.join(str(l) for l in self.global_code))
            raise SyntaxError('expressions found outside of main function:\n%s' % lines_str)
        elif 'main' in self.functions:
            return
        else:
            token_def = Token('ID', 'def', -1, -1)
            token_main = Token('ID', 'main', -1, -1)
            token_return_type = Token('ID', 'int', -1, -1)
            self.register_function([
                token_def,
                token_main,
                [],
                token_return_type,
                ])
            self.compile_def (
                    token_def,
                    token_main,
                    [],
                    token_return_type,
                    *self.global_code)

    @log_compile
    def compile_statement(self, statement):
        c = self.compile_expression(statement)
        if isinstance(c, str):
            if c[0] + c[-1] == '()':
                return c[1:-1] + ';'
            else:
                return c + ';'
        else:
            return c

    @log_compile
    def compile_expression(self, statements):
        if isinstance(statements, Token):
            if statements.typ == 'ID':
                return self.compile_variable(statements)
            else:
                return CompiledExpression(statements.value)
        else:
            token_func_name, *args = statements
            func_name = token_func_name.value
            if func_name in self.keyword_compile_functions.keys():
                return self.keyword_compile_functions[func_name](*statements)
            elif self.is_a_macro(func_name):
                return self.compile_macro(*statements)
            else:
                return self.compile_call(*statements)


    @scope
    @log_compile
    def compile_def(self, match_token,
            function_name_token,
            args,
            return_type_exp,
            *body
            ):

        function_name = function_name_token.value
        return_type = parse_type(return_type_exp)

        call_sig = '{}({})'.format(
            function_name,
            self.compile_def_arguments(args),
            )
        
        ce = self.compile_begin(match_token._replace(value='begin'),*body)
        compiled_body = ce.pre + ['return %s;' % ce.exp]
        new_body = self.compile_variable_declarations() + compiled_body

        function_header = self.compile_variable_declaration(call_sig, return_type)

        f = self.functions[function_name]
        f.compiled_header = function_header
        f.compiled_body = new_body

    @log_compile
    def compile_variable_declarations(self):
        declarations = []
        cs = self.current_scope()
        #pp(s)
        for k, v in sorted(cs.items()):
            var_name = v.name
            var_type = v.type
            var_scope = v.scope
            #print(lvalue, var_type, var_scope)
            if var_scope == 'local':
                l = self.compile_variable_declaration(var_name, var_type)
                r = self.default_value(var_type)
                declarations.append('%s = %s;' % (l, r))
        return declarations

    @log_compile
    def compile_def_arguments(self, arguments):
        paired_args = [(n, t) for n, t in grouper(2, arguments)]
        for n, t in paired_args:
            self.declare(n, t, 'argument')
        return ', '.join( self.compile_variable_declaration(
            n.value,
            parse_type(t),
            ) for n, t in paired_args)

    @log_compile
    def compile_begin(self, match_token,
            *expressions
            ):
        pre = []
        for expression in expressions[:-1]:
            ce = self.compile_expression(expression)
            pre.extend(ce.pre)
            if ce.exp not in self.current_scope():
                pre.append(ce.exp + ';')

        ce = self.compile_expression(expressions[-1])
        pre.extend(ce.pre)
        final_expression = ce.exp

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

    @log_compile
    def compile_call(self,
            function_name_token,
            *args):
        pre = []

        function_name = function_name_token.value

        self.function_calls.append(function_name)

        compiled_args = []
        for arg in args:
            ce = self.compile_expression(arg)
            pre.extend(ce.pre)
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

        for f in functions:
            indent(f.compile())
            print()

        indent(main_function.compile())
        print()


    def compile_variable_declaration(self,
            name,
            var_type
            ):
        if isinstance(var_type, list):
            if var_type[0] == 'cast':
                type_stack = var_type[1][::-1]
            elif var_type[0] == 'Array':
                type_stack = var_type[:3][::-1]
            else:
                type_stack = var_type[::-1]

            l = [type_stack.pop(0)]
            r = [name] if name else []

            previous_t = None
            while type_stack:
                t = type_stack.pop()
                if previous_t == None:
                    pass
                elif t != previous_t:
                    r.insert(0, '(')
                    r.append(')')

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

                previous_t = t
            return '%s %s' % (''.join(l), ''.join(r))
        else:
            return '%s %s' % (var_type, name)

    @log_compile
    def compile_assignment(self, match_token,
            *args
            ):
        *lvalues, rvalue = args
        exps = lvalues
        for lvalue in lvalues:
            self.declare(lvalue, rvalue)
        exps.append(rvalue)
        return self.compile_infix(
                fake_id('='),
                *exps
                )

    def declare(self, lexp, rexp, scope='local', macro_code=None):
        variable_name = self.root_variable(lexp)
        if variable_name not in self.current_scope():
            et = self.expression_type(rexp)
            self.current_scope()[variable_name] = Variable(
                    variable_name,
                    et,
                    scope,
                    macro_code=macro_code,
                    )

    def root_variable(self, exp):
        return exp.value

    def expression_type(self, exp):
        return ['int']

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
        return '0'

    def compile_code(self, new_code):
        self.code = [new_code]
        self.code_ast = []
        self.parse_code()
        self.extract_type_information()
        r = self.compile_statements()
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

    def compile_prefix(self, match_token,
            exp,
            ):
        prefix = match_token.value
        ce = self.compile_expression(exp)
        format_string = '%s%s' if isinstance(exp, Token) else '%s(%s)'
        exp = format_string % (prefix, ce.exp)
        return CompiledExpression(
                pre=ce.pre,
                exp=exp,
                )

    def compile_suffix(self, match_token,
            exp,
            ):
        prefix = match_token.value
        ce = self.compile_expression(exp)
        exp='%s%s' % (ce.exp, prefix)
        return CompiledExpression(
                pre=ce.pre,
                exp=exp,
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


    @log_compile
    def compile_infix(self, match_token,
            *operands
            ):
        pre = []
        exps = []
        operator = match_token.value
        if len(operands) < 2:
            raise SyntaxError('''infix operator requires at least 2 arguments:''')
        for op in operands:
            ce = self.compile_expression(op)
            if ce.pre:
                pre.extend(ce.pre)
            if isinstance(op, Token):
                exps.append(ce.exp)
            else:
                exps.append('(%s)' % ce.exp)
        exp = '%s' % (' %s ' % operator).join(exps)
        return CompiledExpression(
                pre=pre,
                exp=exp,
                )

    @log_compile
    def compile_infix_two_arguments(self, match_token,
            arg1,
            arg2,
            ):
        return self.compile_infix(match_token, arg1, arg2)

    @log_compile
    def compile_if(self, match_token,
            predicate,
            consequent,
            alternative=None,
            ):
        alternative = alternative or Token('NUMBER', '0', -1, -1)
        pre = []
        return_variable_name = self.genvar('if')
        return_variable = Token(
                'ID',
                return_variable_name,
                -1,
                -1,
                )

        ce_predicate = self.compile_expression(predicate)
        ce_consequent = self.compile_assignment(
                        fake_id('='),
                        return_variable,
                        consequent,
                        )
        ce_alternative = self.compile_assignment(
                        fake_id('='),
                        return_variable,
                        alternative,
                        )

        pre.extend(ce_predicate.pre)

        pre.extend([
            'if (%s) {' % ce_predicate.exp,
            ce_consequent.compile(),
            '} else {',
            ce_alternative.compile(),
            '}',
            ])

        return CompiledExpression(
                pre=pre,
                exp=return_variable_name,
                )

    @log_compile
    def compile_cond(self, match_token, *cases):
        pre = []

        return_variable_name = self.genvar('cond')
        return_variable = Token('ID', return_variable_name, -1, -1,)

        compiled_cases = []
        for predicate, consequent in cases:
            ce_predicate = self.compile_expression(predicate)
            ce_consequent = self.compile_assignment(
                            fake_id('='),
                            return_variable,
                            consequent,
                            )
            compiled_cases.append((ce_predicate, ce_consequent))

        ce_predicate, ce_consequent = compiled_cases.pop(0)
        pre.extend([
            'if (%s) {' % ce_predicate.exp,
            ce_consequent.compile(),
            ])
        for ce_predicate, ce_consequent in compiled_cases:
            if ce_predicate.exp != 'else':
                pre.extend([
                    '} else if (%s) {' % ce_predicate.exp,
                    ce_consequent.compile(),
                    ])
            else:
                pre.extend([
                    '} else {',
                    ce_consequent.compile(),
                    ])

        pre.append('}')


        return CompiledExpression(
                pre=pre,
                exp=return_variable_name,
                )

    @log_compile
    def compile_addition_or_substitution(self, match_token, *operands):
        if len(operands) == 1:
            return self.compile_prefix(match_token, operands[0])
        else:
            return self.compile_infix(match_token, *operands)

    @log_compile
    def compile_comparison(self, match_token, *expressions):
        pre = []
        l = []

        if len(expressions) < 2:
            raise SyntaxError

        compiled_expressions = []
        variable_names = []
        for expression in expressions:
            if isinstance(expression, Token):
                if expression.typ == 'ID':
                    variable_names.append(
                            self.compile_variable(expression).exp
                            )
                else:
                    variable_names.append(expression.value)

            else:
                exp_var = fake_id(self.genvar('comp_exp'))
                variable_names.append(exp_var.value)
                ce = self.compile_assignment(
                        match_token._replace(value='='),
                        exp_var,
                        expression,
                        )
                pre.extend(ce.compile())
                compiled_expressions.append(ce)

        if len(expressions) > 2:
            format_s = '(%s %s %s)'
        else:
            format_s = '%s %s %s'

        l = [format_s % (v, match_token.value, next_v)
                for v, next_v
                in zip(variable_names, variable_names[1:])
                ]

        return CompiledExpression(
                pre=pre,
                exp=' && '.join(l),
                )

    def compile_variable(self, match_token):
        if match_token.value in [
                'true',
                'false',
                'else',
                'EOF',
                ]:
            pass
        elif match_token.value not in self.current_scope():
            raise SyntaxError('reference before assignment: %s' % match_token.value)
        return CompiledExpression(
                match_token.value,
                )

    @log_compile
    def compile_while(self, match_token, predicate, *body):
        return_variable = fake_id(self.genvar('while'))

        ce_predicate = self.compile_expression(predicate)

        while_body = []
        for expression in body[:-1]:
            ce = self.compile_expression(expression)
            while_body.extend(ce.compile())

        ce_return = self.compile_assignment(fake_id('set'), return_variable, body[-1])
        while_body.extend(ce_return.compile())
        while_body.extend(ce_predicate.pre)

        pre = ce_predicate.pre + [
                'while (%s) {' % ce_predicate.exp,
                while_body,
                '}',
                ]

        return CompiledExpression(
                pre=pre,
                exp=return_variable.value,
                )

    @log_compile
    def compile_for(self, match_token,
            setup_exp,
            exit_exp,
            step_exp,
            *body):
        return_variable = fake_id(self.genvar(match_token.value))

        ce_setup = self.compile_expression(setup_exp)
        ce_exit = self.compile_expression(exit_exp)
        ce_step = self.compile_expression(step_exp)

        for_body = []
        for expression in body[:-1]:
            ce = self.compile_expression(expression)
            for_body.extend(ce.compile())

        ce_return = self.compile_assignment(fake_id('set'), return_variable, body[-1])
        for_body.extend(ce_return.compile())
        for_body.extend(ce_step.compile())
        for_body.extend(ce_exit.pre)

        pre = ce_setup.compile() + ce_exit.pre + [
                'while (%s) {' % ce_exit.exp,
                for_body,
                '}',
                ]

        return CompiledExpression(
                pre=pre,
                exp=return_variable.value,
                )

    @log_compile
    def compile_case(self, match_token,
            select_exp,
            *cases):
        return_variable = fake_id(self.genvar('case'))

        ce_select = self.compile_expression(select_exp)

        case_body = []
        for case, *exps in cases:
            if case.value == 'default':
                case_body.append('default:')
            else:
                case_body.append('case %s:' % case.value)
            if exps:
                b = []
                ce = self.compile_assignment(
                        fake_id('set'),
                        return_variable,
                        [fake_id('begin')] + exps,
                        )
                b.extend(ce.compile())
                b.append('break;')
                case_body.append(b)

        pre = ce_select.pre + [
                'switch (%s) {' % ce_select.exp,
                case_body,
                '}',
                ]

        #ce_return = self.compile_assignment(fake_id('set'), return_variable, body[-1])

        #pre = ce_setup.compile() + ce_exit.pre + [
                #'while (%s) {' % ce_exit.exp,
                #for_body,
                #'}',
                #]

        return CompiledExpression(
                pre=pre,
                exp=return_variable.value,
                )

    @log_compile
    def compile_each(self, match_token,
            bind_token,
            range_exp,
            *body
            ):

        start, end, step = parse_range(*range_exp[1:])

        init_exp = [fake_id('set'), bind_token, start]
        limit_exp = [fake_id('<'), bind_token, end]
        step_exp = [fake_id('+='), bind_token, step]

        return self.compile_for(
                match_token,
                init_exp,
                limit_exp,
                step_exp,
                *body
                )

    @log_compile
    def compile_in(self, match_token,
            raw_needle,
            haystack,
            ):

        if isinstance(raw_needle, list):
            needle = fake_id(self.genvar('in'))
            ce_needle = self.compile_assignment(
                    fake_id('set'),
                    needle,
                    raw_needle,
                    )
        else:
            needle = raw_needle
            ce_needle = None

        if isinstance(haystack, list):
            start, end, step = parse_range(*haystack[1:])

            body = []

            body.append([fake_id('<='), start, needle])
            body.append([fake_id('<'), needle, end])

            ce_in = self.compile_infix(
                    match_token._replace(value='&&'),
                    *body
                    )
        else:
            string_without_quotes = haystack.value[1:-1]
            body = []
            for char in string_without_quotes:
                body.append([fake_id('='), needle, fake_char(char)])
            ce_in = self.compile_infix(
                    match_token._replace(value='||'),
                    *body
                    )
        pre = []
        if ce_needle:
            pre.extend(ce_needle.compile())
        pre.extend(ce_in.pre)
        return CompiledExpression(
                pre=pre,
                exp=ce_in.exp,
                )

    @log_compile
    def compile_identity(self, match_token,
            variable_token,
            ):
        return self.compile_expression(variable_token)

    @log_compile
    def compile_macro_definition(self, match_token,
            name_token,
            arguments,
            *body
            ):
        self.declare(
                name_token,
                'macro',
                'macro',
                macro_code=(name_token, arguments, body),
                )
        return self.compile_expression(fake_id('true'))

    @log_compile
    def compile_macro(self, match_token,
            *call_arguments
            ):
        macro_name = match_token.value
        _, arguments, body = self.lookup_variable(macro_name).macro_code

        expanded_body = [fake_id('begin')]
        argument_map = {}

        assert(len(call_arguments) == len(arguments))

        for macro_arg, call_arg in zip(arguments, call_arguments):
            assert(macro_arg.typ == 'ID')
            argument_name = macro_arg.value
            arg_var = fake_id(self.genvar(
                'macro',
                macro_name,
                argument_name,
                ))
            argument_instance = arg_var.value
            argument_map[argument_name] = argument_instance
            expanded_body.append([
                fake_id('set'),
                arg_var,
                call_arg,
                ])

        def r(a):
            if a.typ == 'ID' and a.value in argument_map:
                return a._replace(value=argument_map[a.value])
            else:
                return a

        for statement in body:
            expanded_body.append(map_tree(r, statement))

        return self.compile_expression(expanded_body)

    def is_a_macro(self, function_name):
        atom = self.lookup_variable(function_name)
        if atom is not None and atom.scope == 'macro':
            return True
        else:
            return False

    def lookup_variable(self, name):
        for env in self.enviroment_stack[::-1]:
            if name in env:
                return env[name]

def fake_id(value):
    return Token('ID', value, -1, -1)

def fake_number(value):
    return Token('NUMBER', value, -1, -1)

def fake_char(value):
    return Token('CHAR', "'%s'" % value, -1, -1)

def fake_string(value):
    return Token('STRING', '"%s"' % value, -1, -1)

def rewrite_match_id(new_value, fn):
    def wrapper(*args):
        head, *tail = args
        head = head._replace(value=new_value)
        return fn(head, *tail)
    return wrapper

def parse_range(start, end=None, step=None):
    step = step or fake_number('1')
    if end is None:
        end=start
        start = fake_number('0')
    return start, end, step

if __name__ == '__main__':
    #logging.basicConfig(level=logging.INFO)
    script_name, input_filename = argv
    pc = Compiler()
    pc.add_standard_code()
    pc.add_file(input_filename)
    pc.compile()
    pc.write_output()
    #main()

