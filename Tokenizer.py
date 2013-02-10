import collections
import itertools
import re
from sys import argv

Token = collections.namedtuple('Token', ['typ', 'value', 'line', 'column'])

class TokenizerStageOne:
    def __init__(self, input_string):
        def tokenize(s):
            token_specification = [
                ('OPEN_PAREN', r'\('),
                ('CLOSE_PAREN', r'\)'),
                ('NUMBER',  r'\d+(\.\d*)?'),
                ('STRING',  r'"(\\.|[^"])*"'),
                ('BLANK_LINE', r'(?<=\n)\s*\n'),
                ('NEWLINE', r'\n'),
                ('INDENT', r'(?<=\n) +'),
                ('SKIP',    r'[ \t]'),
                ('ID',    r'[^\s\(\)"]+'),
            ]
            tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
            get_token = re.compile(tok_regex).match
            line = 1
            pos = line_start = 0
            mo = get_token(s)
            while mo is not None:
                typ = mo.lastgroup

                if typ != 'SKIP':
                    val = mo.group(typ)
                    if typ == 'OPERATOR' and val in side_effect_operator:
                        typ = 'SIDE_EFFECT_OPERATOR'
                    if typ != 'BLANK_LINE':
                        if typ == 'ID':
                            def replace_hyphen(x):
                                if x == '-':
                                    return '_'
                                else:
                                    return x
                            val = ''.join(map(replace_hyphen,re.split('(->|-)',val)))
                            yield Token(typ, val, line, mo.start()-line_start)
                        else:
                            yield Token(typ, val, line, mo.start()-line_start)

                pos = mo.end()
                mo = get_token(s, pos)

                if typ in ['NEWLINE', 'BLANK_LINE']:
                    line_start = pos
                    line += 1

            if pos != len(s):
                raise RuntimeError('Unexpected character %r on line %d' %(s[pos], line))

        self.tokens = tokenize(input_string)
        self.has_more_tokens = True
        self.advance()

    def advance(self):
        try:
            self.token = next(self.tokens)
        except StopIteration:
            self.has_more_tokens = False


class Tokenizer:
    def __init__(self, input_string):
        def tokenize(s):
            ts = TokenizerStageOne(s)

            call_depth = 0
            indent_depth = 0

            while ts.has_more_tokens:
                t = ts.token
                if t.typ == 'NEWLINE':
                    yield t
                    a = t
                    ts.advance()
                    b = ts.token
                    if b.typ == 'INDENT':
                        ts.advance()
                        line_indent = len(b.value) // 4
                        if line_indent == indent_depth:
                            pass
                        elif line_indent > indent_depth:
                            yield Token('BLOCK_START', '', b.line, b.column)
                            indent_depth = line_indent
                        else:
                            while indent_depth > line_indent:
                                indent_depth -= 1
                                yield Token('BLOCK_END', '', b.line, b.column)
                    else:
                        while indent_depth:
                            indent_depth -= 1
                            yield Token('BLOCK_END', '', a.line, a.column)
                else:
                    if t.typ == 'ID':
                        for v in split_id(t.value):
                            if v == ':':
                                yield Token('ID', 'method', t.line, t.column)
                            elif v in '(':
                                yield Token('OPEN_PAREN', '(', t.line, t.column)
                            elif v in ')':
                                yield Token('CLOSE_PAREN', ')', t.line, t.column)
                            elif v == '':
                                raise ValueError('Error spliting ID', t)
                            else:
                                yield Token('ID', v, t.line, t.column)
                    else:
                        yield t
                    ts.advance()

        self.tokens = tokenize(input_string)
        self.has_more_tokens = True
        self.advance()

    def advance(self):
        try:
            self.token = next(self.tokens)
        except StopIteration:
            self.has_more_tokens = False

    def skip(self, typ):
        if self.token.typ == typ:
            r = self.token.value
            self.advance()
            return r
        else:
            expected(typ, found=self.token.typ)

    def at_keyword(self, keyword):
        return self.token.typ == 'KEYWORD' and self.token.value == keyword

def split_id(value):
    r = []
    if value in [':','->']:
        return [value]
    if value == '@':
        return ['self']
    s = re.split('(@|:|->)', value)

    if s[0] == '':
        if s[1] == '@':
            s.pop(0)
            s.pop(0)
            r.extend(('->', 'self'))
        else:
            s.pop(0)

    for a in s:
        if a == '->':
            if r[0] != '->':
                r.insert(0, a)
            else:
                pass
        elif a == ':':
            if r[0] == 'method':
                raise SyntaxError('found too many ":"')
            else:
                r.insert(0, 'method')
        else:
            r.append(a)

    if r[0] == '->':
        r.insert(0, '(')
        r.append(')')

    return r

def expected(wanted, found):
    raise SyntaxError('wanted: %s; found: %s' % (wanted, found))

if __name__ == "__main__":
    input_text = open(argv[1]).read()

    #ts = TokenizerStageOne(input_text)
    #for t in ts.tokens:
        #print (t)

    #print('-----')

    ts = Tokenizer(input_text)
    while ts.has_more_tokens:
        print(ts.token)
        ts.advance()

