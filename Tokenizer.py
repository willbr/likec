import collections
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
                if t.typ == 'BLANK_LINE':
                    ts.advance()
                elif t.typ == 'NEWLINE':
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
                            indent_depth = line_indent
                            yield Token('BLOCK_END', '', b.line, b.column)
                    else:
                        while indent_depth:
                            indent_depth -= 1
                            yield Token('BLOCK_END', '', a.line, a.column)
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

def expected(wanted, found):
    raise SyntaxError('wanted: %s; found: %s' % (wanted, found))

if __name__ == "__main__":
    input_text = open(argv[1]).read()

    ts = TokenizerStageOne(input_text)
    for t in ts.tokens:
        print (t)

    print('-----')

    ts = Tokenizer(input_text)
    while ts.has_more_tokens:
        print(ts.token)
        ts.advance()

