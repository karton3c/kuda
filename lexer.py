import re

# Typy tokenów
TT_NUMBER    = 'NUMBER'
TT_STRING    = 'STRING'
TT_BOOL      = 'BOOL'
TT_IDENT     = 'IDENT'
TT_ASSIGN    = 'ASSIGN'
TT_PLUS      = 'PLUS'
TT_MINUS     = 'MINUS'
TT_MUL       = 'MUL'
TT_DIV       = 'DIV'
TT_MOD       = 'MOD'
TT_EQ        = 'EQ'
TT_NEQ       = 'NEQ'
TT_LT        = 'LT'
TT_GT        = 'GT'
TT_LTE       = 'LTE'
TT_GTE       = 'GTE'
TT_LPAREN    = 'LPAREN'
TT_RPAREN    = 'RPAREN'
TT_LBRACKET  = 'LBRACKET'
TT_RBRACKET  = 'RBRACKET'
TT_LBRACE    = 'LBRACE'
TT_RBRACE    = 'RBRACE'
TT_COLON     = 'COLON'
TT_PLUS_EQ   = 'PLUS_EQ'
TT_MINUS_EQ  = 'MINUS_EQ'
TT_MUL_EQ    = 'MUL_EQ'
TT_DIV_EQ    = 'DIV_EQ'
TT_COMMA     = 'COMMA'
TT_DOT       = 'DOT'
TT_NEWLINE   = 'NEWLINE'
TT_INDENT    = 'INDENT'
TT_DEDENT    = 'DEDENT'
TT_EOF       = 'EOF'

# Słowa kluczowe Kuda
KEYWORDS = {
    'Matrix',
    'if', 'othif', 'other',
    'repeat', 'each', 'in', 'til',
    'fun', 'give', 'return',
    'model', 'use', 'as',
    'try', 'fail',
    'out',
    'and', 'or', 'not',
    'True', 'False', 'None',
    # Note: 'self' is intentionally NOT a keyword - it should be a regular identifier
    'break', 'continue',
}

class Token:
    def __init__(self, type_, value, line=0):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {repr(self.value)}, line={self.line})'


class LexerError(Exception):
    def __init__(self, msg, line):
        super().__init__(f'[Kuda LexerError] Line {line}: {msg}')


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens = []
        self.indent_stack = [0]
        self.paren_depth = 0  # licznik otwartych ( [ {

    def current(self):
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.source):
            return self.source[p]
        return None

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def tokenize(self):
        while self.pos < len(self.source):
            self._next_token()

        # Zamknij wszystkie otwarte wcięcia
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TT_DEDENT, None, self.line))

        self.tokens.append(Token(TT_EOF, None, self.line))
        return self.tokens

    def _next_token(self):
        ch = self.current()

        # Komentarz
        if ch == '#':
            while self.current() and self.current() != '\n':
                self.advance()
            return

        # Nowa linia + wcięcia
        if ch == '\n':
            self.advance()
            # Wewnątrz nawiasów/list ignorujemy newline i wcięcia
            if self.paren_depth > 0:
                self._skip_whitespace_and_newlines()
                return
            self.tokens.append(Token(TT_NEWLINE, '\n', self.line))
            self._handle_indent()
            return

        # Białe znaki (nie nowa linia)
        if ch in ' \t\r':
            self.advance()
            return

        # Liczby
        if ch.isdigit() or (ch == '.' and self.peek() and self.peek().isdigit()):
            self._read_number()
            return

        # Stringi
        if ch in ('"', "'"):
            self._read_string(ch)
            return

        # Identyfikatory i słowa kluczowe
        if ch.isalpha() or ch == '_':
            self._read_ident()
            return

        # Operatory i symbole
        self._read_symbol()

    def _skip_whitespace_and_newlines(self):
        """Pomija białe znaki i newline wewnątrz nawiasów."""
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r\n':
            if self.source[self.pos] == '\n':
                self.line += 1
            self.pos += 1

    def _handle_indent(self):
        # Policz spacje na początku linii
        spaces = 0
        while self.pos < len(self.source) and self.source[self.pos] in ' \t':
            if self.source[self.pos] == '\t':
                spaces += 4
            else:
                spaces += 1
            self.pos += 1

        # Pomiń puste linie i komentarze — ale zachowaj pozycję
        if self.pos < len(self.source) and self.source[self.pos] in ('\n', '#'):
            return

        # Pomiń też linie złożone tylko z białych znaków
        if self.pos >= len(self.source):
            return

        current_indent = self.indent_stack[-1]

        if spaces > current_indent:
            self.indent_stack.append(spaces)
            self.tokens.append(Token(TT_INDENT, spaces, self.line))
        elif spaces < current_indent:
            while self.indent_stack[-1] > spaces:
                self.indent_stack.pop()
                self.tokens.append(Token(TT_DEDENT, spaces, self.line))

    def _read_number(self):
        start = self.pos
        is_float = False
        while self.current() and (self.current().isdigit() or self.current() == '.'):
            if self.current() == '.':
                is_float = True
            self.advance()
        val = self.source[start:self.pos]
        value = float(val) if is_float else int(val)
        self.tokens.append(Token(TT_NUMBER, value, self.line))

    def _read_string(self, quote):
        self.advance()  # pomiń otwierający cudzysłów
        start = self.pos
        while self.current() and self.current() != quote:
            if self.current() == '\\':
                self.advance()
            self.advance()
        value = self.source[start:self.pos]
        self.advance()  # pomiń zamykający cudzysłów
        # Obsługa escape sequences
        value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
        self.tokens.append(Token(TT_STRING, value, self.line))

    def _read_ident(self):
        start = self.pos
        while self.current() and (self.current().isalnum() or self.current() == '_'):
            self.advance()
        value = self.source[start:self.pos]
        if value == 'True':
            self.tokens.append(Token(TT_BOOL, True, self.line))
        elif value == 'False':
            self.tokens.append(Token(TT_BOOL, False, self.line))
        else:
            self.tokens.append(Token(value if value in KEYWORDS else TT_IDENT, value, self.line))

    def _read_symbol(self):
        ch = self.advance()
        line = self.line

        two = ch + (self.current() or '')

        if two == '==':
            self.advance(); self.tokens.append(Token(TT_EQ, '==', line))
        elif two == '!=':
            self.advance(); self.tokens.append(Token(TT_NEQ, '!=', line))
        elif two == '<=':
            self.advance(); self.tokens.append(Token(TT_LTE, '<=', line))
        elif two == '>=':
            self.advance(); self.tokens.append(Token(TT_GTE, '>=', line))
        elif two == '+=':
            self.advance(); self.tokens.append(Token(TT_PLUS_EQ, '+=', line))
        elif two == '-=':
            self.advance(); self.tokens.append(Token(TT_MINUS_EQ, '-=', line))
        elif two == '*=':
            self.advance(); self.tokens.append(Token(TT_MUL_EQ, '*=', line))
        elif two == '/=':
            self.advance(); self.tokens.append(Token(TT_DIV_EQ, '/=', line))
        elif ch == '=':
            self.tokens.append(Token(TT_ASSIGN, '=', line))
        elif ch == '<':
            self.tokens.append(Token(TT_LT, '<', line))
        elif ch == '>':
            self.tokens.append(Token(TT_GT, '>', line))
        elif ch == '+':
            self.tokens.append(Token(TT_PLUS, '+', line))
        elif ch == '-':
            self.tokens.append(Token(TT_MINUS, '-', line))
        elif ch == '*':
            self.tokens.append(Token(TT_MUL, '*', line))
        elif ch == '/':
            self.tokens.append(Token(TT_DIV, '/', line))
        elif ch == '%':
            self.tokens.append(Token(TT_MOD, '%', line))
        elif ch == '(':
            self.paren_depth += 1
            self.tokens.append(Token(TT_LPAREN, '(', line))
        elif ch == ')':
            self.paren_depth -= 1
            self.tokens.append(Token(TT_RPAREN, ')', line))
        elif ch == '[':
            self.paren_depth += 1
            self.tokens.append(Token(TT_LBRACKET, '[', line))
        elif ch == ']':
            self.paren_depth -= 1
            self.tokens.append(Token(TT_RBRACKET, ']', line))
        elif ch == '{':
            self.paren_depth += 1
            self.tokens.append(Token(TT_LBRACE, '{', line))
        elif ch == '}':
            self.paren_depth -= 1
            self.tokens.append(Token(TT_RBRACE, '}', line))
        elif ch == ':':
            self.tokens.append(Token(TT_COLON, ':', line))
        elif ch == ',':
            self.tokens.append(Token(TT_COMMA, ',', line))
        elif ch == '.':
            self.tokens.append(Token(TT_DOT, '.', line))
        else:
            raise LexerError(f"Unknown character: '{ch}'", line)