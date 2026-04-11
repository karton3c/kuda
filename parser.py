from lexer import *

# === Węzły AST ===

class NumberNode:
    def __init__(self, value, line=0): self.value = value; self.line = line

class StringNode:
    def __init__(self, value, line=0): self.value = value; self.line = line

class BoolNode:
    def __init__(self, value, line=0): self.value = value; self.line = line

class NoneNode:
    def __init__(self, line=0): self.line = line

class IdentNode:
    def __init__(self, name, line=0): self.name = name; self.line = line

class AssignNode:
    def __init__(self, name, value, line=0): self.name = name; self.value = value; self.line = line

class BinOpNode:
    def __init__(self, left, op, right, line=0): self.left = left; self.op = op; self.right = right; self.line = line

class UnaryOpNode:
    def __init__(self, op, operand, line=0): self.op = op; self.operand = operand; self.line = line

class CallNode:
    def __init__(self, func, args, line=0): self.func = func; self.args = args; self.line = line

class AttrNode:
    def __init__(self, obj, attr, line=0): self.obj = obj; self.attr = attr; self.line = line

class IndexNode:
    def __init__(self, obj, index, line=0): self.obj = obj; self.index = index; self.line = line

class IndexAssignNode:
    def __init__(self, target, value, line=0): self.target = target; self.value = value; self.line = line

class ListNode:
    def __init__(self, elements, line=0): self.elements = elements; self.line = line

class TupleNode:
    def __init__(self, elements, line=0): self.elements = elements; self.line = line

class DictNode:
    def __init__(self, pairs, line=0): self.pairs = pairs; self.line = line  # lista (klucz, wartość)

class AugAssignNode:
    def __init__(self, name, op, value, line=0): self.name = name; self.op = op; self.value = value; self.line = line

class ListCompNode:
    def __init__(self, expr, var, iterable): self.expr = expr; self.var = var; self.iterable = iterable

class IfNode:
    def __init__(self, cases, else_body):
        self.cases = cases      # lista (warunek, ciało)
        self.else_body = else_body

class RepeatNode:
    def __init__(self, count, body): self.count = count; self.body = body

class EachNode:
    def __init__(self, var, iterable, body): self.var = var; self.iterable = iterable; self.body = body

class EachUnpackNode:
    def __init__(self, vars, iterable, body): self.vars = vars; self.iterable = iterable; self.body = body

class TilNode:
    def __init__(self, condition, body): self.condition = condition; self.body = body

class FunNode:
    def __init__(self, name, params, body): self.name = name; self.params = params; self.body = body

class AnonFunNode:
    def __init__(self, params, body): self.params = params; self.body = body

class GiveNode:
    def __init__(self, value): self.value = value

class ModelNode:
    def __init__(self, name, body): self.name = name; self.body = body

class NetNode:
    def __init__(self, name, params): self.name = name; self.params = params
    # params = dict of ~key -> value node

class NetLoadNode:
    def __init__(self, name, path_node):
        self.name = name
        self.path_node = path_node
        self.body = []  # empty — no block body, needed by generic exec loops

class UseNode:
    def __init__(self, module, alias=None, filepath=None, absolute=False):
        self.module = module      # Python module name (e.g. 'numpy')
        self.alias = alias        # optional alias
        self.filepath = filepath  # Kuda file path (e.g. 'utils.kuda')
        self.absolute = absolute  # True if @"path" (relative to CWD)

class ExternNode:
    def __init__(self, name, params, ret_type='double', c_file=None):
        self.name = name        # nazwa funkcji C (None jeśli to extern "plik.c")
        self.params = params    # lista (nazwa, typ)
        self.ret_type = ret_type
        self.c_file = c_file   # ścieżka do pliku .c do dołączenia

class OutNode:
    def __init__(self, value): self.value = value

class TryNode:
    def __init__(self, try_body, fail_clauses):
        self.try_body = try_body
        # fail_clauses: list of (error_type, var_name, body)
        # error_type: str like 'TypeError', 'ValueError', or None = catch all
        # var_name: str or None
        self.fail_clauses = fail_clauses

class BreakNode:
    pass

class ContinueNode:
    pass

class ProgramNode:
    def __init__(self, statements): self.statements = statements


# === Parser ===

class ParseError(Exception):
    def __init__(self, msg, line):
        super().__init__(f'[Kuda ParseError] Line {line}: {msg}')


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return self.tokens[-1]

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise ParseError(f"Expected '{type_}', got '{tok.type}' ('{tok.value}')", tok.line)
        return self.advance()

    def expect_identifier(self):
        """
        Expects an identifier but also accepts some keywords that can be used as identifiers.
        This makes the language more forgiving in contexts where keywords are commonly used
        as variable/parameter names (like 'self', 'model', etc.)
        """
        tok = self.current()
        # Accept actual identifiers or certain keywords that are commonly used as names
        allowed_as_idents = {'self', 'model', 'fun', 'Matrix'}
        if tok.type == TT_IDENT or tok.value in allowed_as_idents:
            value = tok.value
            self.advance()
            return value
        raise ParseError(f"Expected identifier, got '{tok.type}' ('{tok.value}')", tok.line)

    def skip_newlines(self):
        while self.current().type == TT_NEWLINE:
            self.advance()

    def skip_newlines_and_indent(self):
        """Używane wewnątrz [], {} gdzie INDENT/DEDENT nie mają znaczenia"""
        while self.current().type in (TT_NEWLINE, TT_INDENT, TT_DEDENT):
            self.advance()

    def parse(self):
        self.skip_newlines()
        statements = []
        while self.current().type != TT_EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        return ProgramNode(statements)

    def parse_block(self):
        # Ignoruj puste linie przed blokiem
        while self.current().type == TT_NEWLINE:
            self.advance()
        self.expect(TT_INDENT)
        self.skip_newlines()
        statements = []
        while self.current().type not in (TT_DEDENT, TT_EOF):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        if self.current().type == TT_DEDENT:
            self.advance()
        return statements

    def parse_statement(self):
        tok = self.current()

        if tok.type == TT_NEWLINE:
            self.advance()
            return None

        if tok.type == 'use':
            return self.parse_use()

        if tok.type == 'if':
            return self.parse_if()

        if tok.type == 'repeat':
            return self.parse_repeat()

        if tok.type == 'each':
            return self.parse_each()

        if tok.type == 'til':
            return self.parse_til()

        if tok.type == 'fun':
            # peek: if next token after 'fun' is IDENT then named function statement
            # if next is LPAREN then anonymous function expression
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == TT_LPAREN:
                return self.parse_anon_fun()
            return self.parse_fun()

        if tok.type == 'model':
            return self.parse_model()
        if tok.type == 'net':
            return self.parse_net()
        if tok.type == 'extern':
            return self.parse_extern()

        # ~name = net.load("file.json") — top-level net load
        if tok.type == TT_TILDE:
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == TT_IDENT:
                # peek further: IDENT ASSIGN net . load ( ...
                p = self.pos + 2
                def _peek(offset):
                    return self.tokens[p + offset] if p + offset < len(self.tokens) else None
                if (_peek(0) and _peek(0).type == TT_ASSIGN and
                    _peek(1) and _peek(1).type == 'net' and
                    _peek(2) and _peek(2).type == TT_DOT and
                    _peek(3) and _peek(3).type == TT_IDENT and _peek(3).value == 'load' and
                    _peek(4) and _peek(4).type == TT_LPAREN):
                    return self.parse_net_load()

        if tok.type in ('give', 'return'):
            return self.parse_give()

        if tok.type == 'try':
            return self.parse_try()

        if tok.type == 'break':
            self.advance()
            self._end_statement()
            return BreakNode()

        if tok.type == 'continue':
            self.advance()
            self._end_statement()
            return ContinueNode()

        if tok.type == 'out':
            return self.parse_out()

        # Przypisanie lub wyrażenie
        return self.parse_assign_or_expr()

    def _end_statement(self):
        if self.current().type == TT_NEWLINE:
            self.advance()

    def parse_use(self):
        self.advance()  # 'use'

        # use "file.kuda"  or  use @"file.kuda"
        absolute = False
        if self.current().type == TT_AT:
            self.advance()  # @
            absolute = True
        if self.current().type == TT_STRING:
            filepath = self.advance().value
            self._end_statement()
            return UseNode(module=None, filepath=filepath, absolute=absolute)

        # use numpy  or  use numpy as np
        name = self.expect(TT_IDENT).value
        alias = None
        if self.current().type == 'as':
            self.advance()  # 'as'
            alias = self.expect_identifier()
        self._end_statement()
        return UseNode(name, alias)

    def parse_extern(self):
        self.advance()  # 'extern'

        # extern "plik.c" — dołącz plik C do kompilacji
        if self.current().type == TT_STRING:
            c_file = self.advance().value
            self._end_statement()
            return ExternNode(name=None, params=[], c_file=c_file)

        # extern [typ] nazwa(params) — deklaracja funkcji C
        ret_type = 'double'
        if self.current().type == TT_IDENT and self.current().value in ('void', 'str', 'double', 'int'):
            ret_type = self.advance().value

        name = self.expect(TT_IDENT).value
        self.expect(TT_LPAREN)

        params = []
        while self.current().type != TT_RPAREN:
            if self.current().type == TT_IDENT and self.current().value in ('double', 'str', 'int', 'void'):
                ptype = self.advance().value
            else:
                ptype = 'double'
            if self.current().type == TT_IDENT:
                pname = self.advance().value
            else:
                pname = f'arg{len(params)}'
            params.append((pname, ptype))
            if self.current().type == TT_COMMA:
                self.advance()

        self.expect(TT_RPAREN)
        self._end_statement()
        return ExternNode(name, params, ret_type)

    def parse_out(self):
        self.advance()  # 'out'
        self.expect(TT_LPAREN)
        value = self.parse_expr()
        self.expect(TT_RPAREN)
        self._end_statement()
        return OutNode(value)

    def parse_if(self):
        cases = []

        self.advance()  # 'if'
        cond = self.parse_expr()
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        cases.append((cond, body))

        while self.current().type == 'othif':
            self.advance()
            cond = self.parse_expr()
            self.expect(TT_COLON)
            self._end_statement()
            body = self.parse_block()
            cases.append((cond, body))

        else_body = None
        if self.current().type == 'other':
            self.advance()
            self.expect(TT_COLON)
            self._end_statement()
            else_body = self.parse_block()

        return IfNode(cases, else_body)

    def parse_repeat(self):
        self.advance()  # 'repeat'
        count = self.parse_expr()
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return RepeatNode(count, body)

    def parse_each(self):
        self.advance()  # 'each'
        first_var = self.expect_identifier()
        if self.current().type == TT_COMMA:
            # Tuple unpacking: each x, t in data:
            vars = [first_var]
            while self.current().type == TT_COMMA:
                self.advance()
                vars.append(self.expect_identifier())
            self.expect('in')
            iterable = self.parse_expr()
            self.expect(TT_COLON)
            self._end_statement()
            body = self.parse_block()
            return EachUnpackNode(vars, iterable, body)
        self.expect('in')
        iterable = self.parse_expr()
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return EachNode(first_var, iterable, body)

    def parse_til(self):
        self.advance()  # 'til'
        cond = self.parse_expr()
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return TilNode(cond, body)

    def parse_fun(self):
        self.advance()  # 'fun'
        name = self.expect(TT_IDENT).value
        self.expect(TT_LPAREN)
        params = []
        while self.current().type != TT_RPAREN:
            params.append(self.expect_identifier())
            if self.current().type == TT_COMMA:
                self.advance()
        self.expect(TT_RPAREN)
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return FunNode(name, params, body)

    def parse_anon_fun(self):
        self.advance()  # 'fun'
        self.expect(TT_LPAREN)
        params = []
        while self.current().type != TT_RPAREN:
            params.append(self.expect_identifier())
            if self.current().type == TT_COMMA:
                self.advance()
        self.expect(TT_RPAREN)
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return AnonFunNode(params, body)

    def parse_model(self):
        self.advance()  # 'model'
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return ModelNode(name, body)

    def parse_net(self):
        self.advance()  # 'net'
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)
        self._end_statement()
        # Parse body - only ~key = value lines
        self.expect(TT_INDENT)
        params = {}
        while self.current().type not in (TT_DEDENT, TT_EOF):
            self.skip_newlines()
            if self.current().type == TT_DEDENT:
                break
            # Expect ~ key = value
            if self.current().type == TT_TILDE:
                self.advance()  # ~
                key = self.expect(TT_IDENT).value
                self.expect(TT_ASSIGN)
                value = self.parse_expr()
                params[key] = value
                self._end_statement()
            else:
                self._end_statement()
        if self.current().type == TT_DEDENT:
            self.advance()
        return NetNode(name, params)

    def parse_net_load(self):
        # ~name = net.load("file.json")
        self.advance()  # ~
        name = self.expect(TT_IDENT).value
        self.expect(TT_ASSIGN)   # =
        self.expect('net')       # net (keyword token)
        self.expect(TT_DOT)      # .
        self.advance()           # load (IDENT, already verified in peek)
        self.expect(TT_LPAREN)   # (
        path_node = self.parse_expr()
        self.expect(TT_RPAREN)   # )
        self._end_statement()
        return NetLoadNode(name, path_node)

    def parse_give(self):
        self.advance()  # 'give'
        value = self.parse_expr()
        self._end_statement()
        return GiveNode(value)

    def parse_try(self):
        self.advance()  # 'try'
        self.expect(TT_COLON)
        self._end_statement()
        try_body = self.parse_block()

        fail_clauses = []
        while self.current().type == 'fail':
            self.advance()  # 'fail'

            error_type = None
            var_name = None

            # peek: fail TypeError e:  /  fail e:  /  fail:
            tok = self.current()
            if tok.type == TT_IDENT:
                next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                # fail TypeError e:  — starts with capital = error type
                if tok.value[0].isupper():
                    error_type = self.advance().value
                    # optional var name
                    if self.current().type == TT_IDENT:
                        var_name = self.advance().value
                else:
                    # fail e: — just var name, no type
                    var_name = self.advance().value

            self.expect(TT_COLON)
            self._end_statement()
            body = self.parse_block()
            fail_clauses.append((error_type, var_name, body))

        if not fail_clauses:
            raise ParseError("try without fail", self.current().line)

        return TryNode(try_body, fail_clauses)

    def parse_assign_or_expr(self):
        expr = self.parse_expr()
        line = getattr(expr, 'line', 0)

        if self.current().type == TT_ASSIGN:
            self.advance()
            value = self.parse_expr()
            self._end_statement()
            if isinstance(expr, IdentNode):
                return AssignNode(expr.name, value, line)
            elif isinstance(expr, AttrNode):
                return AssignNode(expr, value, line)
            elif isinstance(expr, IndexNode):
                return IndexAssignNode(expr, value, line)
            else:
                raise ParseError("Invalid left-hand side of assignment", self.current().line)

        # += -= *= /=
        aug_ops = {
            TT_PLUS_EQ: '+', TT_MINUS_EQ: '-', TT_MUL_EQ: '*', TT_DIV_EQ: '/'
        }
        if self.current().type in aug_ops:
            op = aug_ops[self.current().type]
            self.advance()
            value = self.parse_expr()
            self._end_statement()
            if isinstance(expr, IdentNode):
                return AugAssignNode(expr.name, op, value, line)
            else:
                raise ParseError("Invalid left-hand side of augmented assignment", self.current().line)

        self._end_statement()
        return expr

    # === Wyrażenia ===

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == 'or':
            line = self.current().line
            op = self.advance().value
            right = self.parse_and()
            left = BinOpNode(left, op, right, line)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.current().type == 'and':
            line = self.current().line
            op = self.advance().value
            right = self.parse_not()
            left = BinOpNode(left, op, right, line)
        return left

    def parse_not(self):
        if self.current().type == 'not':
            line = self.current().line
            op = self.advance().value
            operand = self.parse_not()
            return UnaryOpNode(op, operand, line)
        return self.parse_compare()

    def parse_compare(self):
        left = self.parse_add()
        while self.current().type in (TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE):
            line = self.current().line
            op = self.advance().value
            right = self.parse_add()
            left = BinOpNode(left, op, right, line)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.current().type in (TT_PLUS, TT_MINUS):
            line = self.current().line
            op = self.advance().value
            right = self.parse_mul()
            left = BinOpNode(left, op, right, line)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.current().type in (TT_MUL, TT_DIV, TT_MOD):
            line = self.current().line
            op = self.advance().value
            right = self.parse_unary()
            left = BinOpNode(left, op, right, line)
        return left

    def parse_unary(self):
        if self.current().type == TT_MINUS:
            line = self.current().line
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOpNode(op, operand, line)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.current().type == TT_DOT:
                line = self.current().line
                self.advance()
                attr = self.expect(TT_IDENT).value
                node = AttrNode(node, attr, line)
            elif self.current().type == TT_LPAREN:
                line = self.current().line
                self.advance()
                args = []
                while self.current().type != TT_RPAREN:
                    args.append(self.parse_expr())
                    if self.current().type == TT_COMMA:
                        self.advance()
                self.expect(TT_RPAREN)
                node = CallNode(node, args, line)
            elif self.current().type == TT_LBRACKET:
                line = self.current().line
                self.advance()
                index = self.parse_expr()
                self.expect(TT_RBRACKET)
                node = IndexNode(node, index, line)
            else:
                break
        return node

    def parse_primary(self):
        tok = self.current()

        if tok.type == TT_NUMBER:
            self.advance()
            return NumberNode(tok.value, tok.line)

        if tok.type == TT_STRING:
            self.advance()
            return StringNode(tok.value, tok.line)

        if tok.type == TT_BOOL:
            self.advance()
            return BoolNode(tok.value, tok.line)

        if tok.value == 'None':
            self.advance()
            return NoneNode(tok.line)

        if tok.type == TT_IDENT:
            self.advance()
            return IdentNode(tok.value, tok.line)

        if tok.type == TT_LPAREN:
            self.advance()
            expr = self.parse_expr()
            if self.current().type == TT_COMMA:
                # To jest krotka
                elements = [expr]
                while self.current().type == TT_COMMA:
                    self.advance()
                    if self.current().type == TT_RPAREN:
                        break
                    elements.append(self.parse_expr())
                self.expect(TT_RPAREN)
                return TupleNode(elements)
            self.expect(TT_RPAREN)
            return expr

        if tok.type == TT_LBRACE:
            self.advance()
            self.skip_newlines_and_indent()
            pairs = []
            while self.current().type != TT_RBRACE:
                key = self.parse_expr()
                self.expect(TT_COLON)
                val = self.parse_expr()
                pairs.append((key, val))
                self.skip_newlines_and_indent()
                if self.current().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines_and_indent()
            self.expect(TT_RBRACE)
            return DictNode(pairs)

        if tok.type == TT_LBRACKET:
            self.advance()
            self.skip_newlines_and_indent()
            elements = []
            while self.current().type != TT_RBRACKET:
                elements.append(self.parse_expr())
                self.skip_newlines_and_indent()
                # list comprehension: [expr each x in lista]
                if self.current().type == 'each' and len(elements) == 1:
                    self.advance()
                    var = self.expect_identifier()
                    self.expect('in')
                    iterable = self.parse_expr()
                    self.skip_newlines_and_indent()
                    self.expect(TT_RBRACKET)
                    return ListCompNode(elements[0], var, iterable)
                if self.current().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines_and_indent()
            self.expect(TT_RBRACKET)
            return ListNode(elements)

        if tok.type == 'fun':
            self.advance()  # consume 'fun' peek token
            next_tok = self.current()
            if next_tok and next_tok.type == TT_LPAREN:
                self.pos -= 1  # back up so parse_anon_fun can advance past 'fun'
                return self.parse_anon_fun()

        raise ParseError(f"Unexpected token: '{tok.type}' ('{tok.value}')", tok.line)