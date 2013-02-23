import collections
import itertools
import re
from sys import argv

Token = collections.namedtuple('Token', ['typ', 'value', 'line', 'column'])

class TokenizerStageOne:
    def __init__(self, input_string):
        def tokenize(s):
            char_regex = r'\'(\\.|.)\''
            token_specification = [
                ('OPEN_PAREN', r'\('),
                ('CLOSE_PAREN', r'\)'),
                ('OPEN_SQUARE', r'\['),
                ('CLOSE_SQUARE', r'\]'),
                ('OPEN_CURLY', r'\{'),
                ('CLOSE_CURLY', r'\}'),
                ('RANGE_NUMBER',  r'\d+\.\.\.?\d+'),
                ('RANGE_CHAR',  r'%s\.\.\.?%s' % (char_regex, char_regex)),
                ('NUMBER',  r'(\+|\-)?\d+(\.\d*)?'),
                ('STRING',  r'"(\\.|[^"])*"'),
                ('STRING_RAW',  r'r"(\\.|[^"])*"'),
                ('CHAR',  char_regex),
                ('BLANK_LINE', r'(?<=\n)\s*\n'),
                ('NEWLINE', r'\n'),
                ('INDENT', r'(?<=\n) +'),
                ('SKIP',    r'[ \t]'),
                ('COMMENT',    r';.*'),
                ('HEREDOC',    r'<<\S+'),
                ('ID',    r'[^\s\(\)\[\]\{\}"]+'),
            ]
            tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
            get_token = re.compile(tok_regex).match
            line = 1
            pos = line_start = 0
            mo = get_token(s)

            hstart = None
            hline = 0

            while mo is not None:
                typ = mo.lastgroup

                if typ != 'SKIP':
                    val = mo.group(typ)
                    if typ == 'HEREDOC':
                        if hstart == None:
                            get_eol = re.compile(r'\n').search
                            hstart = get_eol(s, pos).end()
                        hval = val[2:]

                        rx = r'^%s\s*\n' % hval
                        get_heredoc = re.compile(rx, re.MULTILINE).search

                        hmo = get_heredoc(s, hstart)

                        heredoc_s = s[hstart:hmo.start() - 1] # skip last newline
                        hline += heredoc_s.count('\n')
                        hstart = hmo.end()
                        yield Token('STRING',
                                '"%s"' % heredoc_s.replace('\n', r'\n'),
                                line,
                                mo.start()-line_start)
                    elif typ not in ['BLANK_LINE']:
                        if typ == 'ID':
                            yield Token(typ, val, line, mo.start()-line_start)
                        else:
                            yield Token(typ, val, line, mo.start()-line_start)

                if typ == 'NEWLINE' and hstart:
                    if pos < hstart:
                        pos = hstart
                    else:
                        pos = mo.end()
                    line += hline
                    hline = 0
                    hstart = None
                else:
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
            #print(s)
            ts = TokenizerStageOne(s)

            call_depth = 0
            indent_depth = 0
            sexp_depth = 0

            while ts.has_more_tokens:
                t = ts.token
                #print(t)

                if t.typ == 'NEWLINE' and sexp_depth == 0:
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
                    elif t.typ == 'OPEN_PAREN':
                        sexp_depth += 1
                        yield t
                    elif t.typ == 'CLOSE_PAREN':
                        sexp_depth -= 1
                        yield t
                    elif t.typ == 'INDENT':
                        pass
                    elif t.typ == 'OPEN_SQUARE':
                        yield Token('OPEN_PAREN', '(', t.line, t.column)
                        yield Token('ID', 'deref', t.line, t.column)
                    elif t.typ == 'CLOSE_SQUARE':
                        yield Token('CLOSE_PAREN', ')', t.line, t.column)
                    elif t.typ == 'OPEN_CURLY':
                        yield Token('OPEN_PAREN', '(', t.line, t.column)
                        yield Token('ID', 'fn-shorthand', t.line, t.column)
                    elif t.typ == 'CLOSE_CURLY':
                        yield Token('CLOSE_PAREN', ')', t.line, t.column)
                    elif t.typ.find('RANGE_') == 0:
                        start, middle, end = re.split('(\.+)', t.value)
                        yield Token('OPEN_PAREN', '(', t.line, t.column)
                        yield Token('ID', 'range', t.line, t.column)
                        yield Token('ID', start, t.line, t.column)
                        if len(middle) == 2:
                            yield Token('ID', str(int(end)+1), t.line, t.column)
                        else:
                            yield Token('ID', end, t.line, t.column)
                        yield Token('CLOSE_PAREN', ')', t.line, t.column)
                    elif t.typ == 'STRING_RAW':
                        v = t.value[1:].replace('\\', '\\\\')
                        yield Token('STRING', v, t.line, t.column)
                    else:
                        yield t
                    ts.advance()
            for i in range(indent_depth):
                yield Token('BLOCK_END', '', t.line, t.column)

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

    s = list(filter(None, re.split('(@|:|->)', value)))

    if s[0] == '@':
        s.pop(0)
        r.extend(('->', 'self'))

    for a in s:
        if a == '->':
            if r[0] != '->':
                r.insert(0, a)
            else:
                pass
        elif a == ':':
            if r[0] == 'method':
                raise SyntaxError('found too many: ":"')
            else:
                r.insert(0, 'method')
        elif a == '':
            pass
        else:
            r.append(a)

    if r[0] in ['->']:
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

