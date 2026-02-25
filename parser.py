from lexer import *

# === Węzły AST ===

class NumberNode:
    def __init__(self, value): self.value = value

class StringNode:
    def __init__(self, value): self.value = value

class BoolNode:
    def __init__(self, value): self.value = value

class NoneNode:
    pass

class IdentNode:
    def __init__(self, name): self.name = name

class AssignNode:
    def __init__(self, name, value): self.name = name; self.value = value

class BinOpNode:
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right

class UnaryOpNode:
    def __init__(self, op, operand): self.op = op; self.operand = operand

class CallNode:
    def __init__(self, func, args): self.func = func; self.args = args

class AttrNode:
    def __init__(self, obj, attr): self.obj = obj; self.attr = attr

class IndexNode:
    def __init__(self, obj, index): self.obj = obj; self.index = index

class IndexAssignNode:
    def __init__(self, target, value): self.target = target; self.value = value

class ListNode:
    def __init__(self, elements): self.elements = elements

class TupleNode:
    def __init__(self, elements): self.elements = elements

class DictNode:
    def __init__(self, pairs): self.pairs = pairs  # lista (klucz, wartość)

class AugAssignNode:
    def __init__(self, name, op, value): self.name = name; self.op = op; self.value = value

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

class GiveNode:
    def __init__(self, value): self.value = value

class ModelNode:
    def __init__(self, name, body): self.name = name; self.body = body

class UseNode:
    def __init__(self, module, alias=None):
        self.module = module
        self.alias = alias  # e.g. 'use numpy as np' -> alias = 'np'

class OutNode:
    def __init__(self, value): self.value = value

class TryNode:
    def __init__(self, try_body, fail_body): self.try_body = try_body; self.fail_body = fail_body

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
            return self.parse_fun()

        if tok.type == 'model':
            return self.parse_model()

        if tok.type == 'give':
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
        name = self.expect(TT_IDENT).value
        alias = None
        # Handle: use numpy as np
        if self.current().type == 'as':
            self.advance()  # 'as'
            alias = self.expect_identifier()
        self._end_statement()
        return UseNode(name, alias)

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

    def parse_model(self):
        self.advance()  # 'model'
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)
        self._end_statement()
        body = self.parse_block()
        return ModelNode(name, body)

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
        self.expect('fail')
        self.expect(TT_COLON)
        self._end_statement()
        fail_body = self.parse_block()
        return TryNode(try_body, fail_body)

    def parse_assign_or_expr(self):
        expr = self.parse_expr()

        if self.current().type == TT_ASSIGN:
            self.advance()
            value = self.parse_expr()
            self._end_statement()
            if isinstance(expr, IdentNode):
                return AssignNode(expr.name, value)
            elif isinstance(expr, AttrNode):
                return AssignNode(expr, value)
            elif isinstance(expr, IndexNode):
                return IndexAssignNode(expr, value)
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
                return AugAssignNode(expr.name, op, value)
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
            op = self.advance().value
            right = self.parse_and()
            left = BinOpNode(left, op, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.current().type == 'and':
            op = self.advance().value
            right = self.parse_not()
            left = BinOpNode(left, op, right)
        return left

    def parse_not(self):
        if self.current().type == 'not':
            op = self.advance().value
            operand = self.parse_not()
            return UnaryOpNode(op, operand)
        return self.parse_compare()

    def parse_compare(self):
        left = self.parse_add()
        while self.current().type in (TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE):
            op = self.advance().value
            right = self.parse_add()
            left = BinOpNode(left, op, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.current().type in (TT_PLUS, TT_MINUS):
            op = self.advance().value
            right = self.parse_mul()
            left = BinOpNode(left, op, right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.current().type in (TT_MUL, TT_DIV, TT_MOD):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOpNode(left, op, right)
        return left

    def parse_unary(self):
        if self.current().type == TT_MINUS:
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOpNode(op, operand)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.current().type == TT_DOT:
                self.advance()
                attr = self.expect(TT_IDENT).value
                node = AttrNode(node, attr)
            elif self.current().type == TT_LPAREN:
                self.advance()
                args = []
                while self.current().type != TT_RPAREN:
                    args.append(self.parse_expr())
                    if self.current().type == TT_COMMA:
                        self.advance()
                self.expect(TT_RPAREN)
                node = CallNode(node, args)
            elif self.current().type == TT_LBRACKET:
                self.advance()
                index = self.parse_expr()
                self.expect(TT_RBRACKET)
                node = IndexNode(node, index)
            else:
                break
        return node

    def parse_primary(self):
        tok = self.current()

        if tok.type == TT_NUMBER:
            self.advance()
            return NumberNode(tok.value)

        if tok.type == TT_STRING:
            self.advance()
            return StringNode(tok.value)

        if tok.type == TT_BOOL:
            self.advance()
            return BoolNode(tok.value)

        if tok.value == 'None':
            self.advance()
            return NoneNode()

        if tok.type == TT_IDENT:
            self.advance()
            return IdentNode(tok.value)

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

        raise ParseError(f"Unexpected token: '{tok.type}' ('{tok.value}')", tok.line)