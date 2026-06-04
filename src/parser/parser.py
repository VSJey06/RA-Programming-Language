"""
parser.py — Recursive-descent parser for the RA language.

Converts a flat token stream (from the RA tokenizer) into an AST
defined in ``ra_ast.py``.

Grammar summary
---------------

    program      := stmt*

    stmt         := DbBlock | ClassDef | MethodDef | ObjectStmt
                   | PrintStmt | TypedAssign | AssignStmt
                   | MethodCall | IfStmt | ForStmt | WhileStmt
                   | ReturnStmt | AICallStmt
                   | DbNextStmt | DbBreakStmt

    DbBlock      := 'Db' ':' {stmt} 'db.close'
    ClassDef     := '@Cls.Name' ':' {member}
    MethodDef    := 'M.name' ':' {stmt} '/'
    ObjectStmt   := 'Obj.ClassName' '.' 'VariableName'

    PrintStmt    := 'p' expression
    TypedAssign  := ('S'|'I'|'L') ident [ ('.' ident)+ ] ':' expression
    AssignStmt   := ident '=' expression
    MethodCall   := ident ':' expression

    IfStmt       := '!' 'If.condition' ',' body '#'
                     { '!!' condition ',' body '#' }
                     [ '!' 'Else' body '#' ]

    ForStmt      := '?' 'For.var=start;end' ',' body '#'
    WhileStmt    := '?' 'While.condition' ',' body '#'

    ReturnStmt   := 'R' '.' expression
    AICallStmt   := 'AI' ident '=' expression
    DbNextStmt   := 'db.next'
    DbBreakStmt  := 'db.break'

    expression   := primary { '.' ident } { binary_op primary }
    primary      := STRING | INTEGER | IDENTIFIER
    binary_op    := '==' | '!=' | '>' | '<' | '>=' | '<='
                   | '+' | '-' | '*' | '%' | ';'

All block constructs support automatic closure.  When a sibling construct
or structural boundary is encountered instead of the explicit terminator,
the block is closed implicitly and ``auto_close=True`` is set.

    Explicit terminators
    --------------------
        Db block    :  db.close
        Class       :  @  (or @.close)
        Method      :  /  (or /.close)
        If / ElseIf :  #
        For / While :  #
"""

from __future__ import annotations

from typing import Optional

from lexer.tokens import Token, TokenType
from parser.ra_ast import (
    AICallNode,
    AssignmentNode,
    BinaryOpNode,
    ClassNode,
    DbBreakNode,
    DbLoadNode,
    DbNextNode,
    DbNode,
    DbSaveNode,
    ElseIfNode,
    ElseNode,
    ForNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    MethodCallNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    ObjectNode,
    PrintNode,
    ProgramNode,
    PropertyAccessNode,
    RelationAssignmentNode,
    ReturnNode,
    WhileNode,
)


# ===========================================================================
# ParseError
# ===========================================================================

class ParseError(Exception):
    """Raised when the parser encounters a syntax error.

    Attributes
    ----------
    token : Token — the token that triggered the error.
    """

    def __init__(self, message: str, token: Token) -> None:
        super().__init__(
            f"[line {token.line}] ParseError: {message}, "
            f"got {token.type.name}({token.value!r})"
        )
        self.token = token


# ===========================================================================
# Parser
# ===========================================================================

class Parser:
    """Recursive-descent parser for the RA language.

    Parameters
    ----------
    tokens : list[Token] — flat token stream from ``tokenizer.tokenize()``.
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos    = 0
        self._body_terminators: frozenset[TokenType] = frozenset()

    # ── Token helpers ────────────────────────────────────────────────────

    def _current(self) -> Token:
        """Return the token at the current position, or an EOF sentinel."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        last = self.tokens[-1] if self.tokens else None
        return Token(TokenType.EOF, None, getattr(last, "line", 1), 0)

    def _check(self, *types: TokenType) -> bool:
        """Return True if the current token type matches any of *types*."""
        return self._current().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        """If the current token matches any of *types*, consume and return it.

        Returns None when no match.
        """
        if self._check(*types):
            return self._advance()
        return None

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self._current()
        self.pos += 1
        return tok

    def _consume(self, expected: TokenType, message: str) -> Token:
        """Assert the current token is *expected*, consume it, and return it.

        Raises ``ParseError`` with *message* on mismatch.
        """
        if self._check(expected):
            return self._advance()
        raise ParseError(message, self._current())

    # ── Main entry point ─────────────────────────────────────────────────

    def parse(self) -> ProgramNode:
        """Parse the full token stream into a ``ProgramNode``."""
        body: list[Node] = []
        while not self._check(TokenType.EOF):
            stmt = self._parse_stmt()
            if stmt is not None:
                body.append(stmt)
        return ProgramNode(line=1, body=body)

    # ── Generic body parser ──────────────────────────────────────────────

    def _parse_body(self, terminators: frozenset[TokenType] = frozenset()) -> list[Node]:
        """Parse a sequence of statements until a terminator or EOF.

        Propagates structural terminators (``@``, ``/``, ``db.close``, ``!``, ``#``)
        from enclosing constructs so that nested blocks correctly respect
        parent boundaries.

        Parameters
        ----------
        terminators : token types that should stop this body.
        """
        body: list[Node] = []
        active = self._body_terminators | terminators
        saved = self._body_terminators
        self._body_terminators = active
        while not self._check(TokenType.EOF):
            if self._check(*active):
                break
            stmt = self._parse_stmt()
            if stmt is not None:
                body.append(stmt)
        self._body_terminators = saved
        return body

    # ── Statement dispatch ───────────────────────────────────────────────

    def _parse_stmt(self) -> Optional[Node]:
        """Dispatch to the appropriate parse method.

        Returns None for structural tokens that should be skipped
        (commas).  Raises ``ParseError`` for unrecognised tokens.
        """
        tok = self._current()
        tt  = tok.type

        if tt == TokenType.DB:
            return self._parse_db()
        if tt == TokenType.AT:
            return self._parse_at_stmt()
        if tt == TokenType.OBJ:
            return self._parse_object()
        if tt == TokenType.M:
            return self._parse_method()
        if tt == TokenType.P:
            return self._parse_print()
        if tt == TokenType.R:
            return self._parse_return()
        if tt == TokenType.AI:
            return self._parse_ai()
        if tt in (TokenType.S, TokenType.I, TokenType.L):
            return self._parse_typed_assignment()
        if tt == TokenType.IDENTIFIER:
            return self._parse_identifier_stmt()
        if tt == TokenType.BANG:
            return self._parse_bang_stmt()
        if tt == TokenType.QUESTION:
            return self._parse_question_stmt()
        if tt == TokenType.DB_NEXT:
            self._advance()
            return DbNextNode(line=tok.line)
        if tt == TokenType.DB_BREAK:
            self._advance()
            return DbBreakNode(line=tok.line)
        if tt == TokenType.DB_CLOSE:
            raise ParseError(
                "Unexpected 'db.close' outside of a Db block. "
                "Did you forget 'Db:' ?",
                tok,
            )
        if tt == TokenType.METHOD_CLOSE:
            raise ParseError(
                "Unexpected '/.close' outside of a method body. "
                "Did you forget 'M.name:' ?",
                tok,
            )
        if tt == TokenType.COMMA:
            self._advance()
            return None

        if tt == TokenType.AT_CLOSE:
            raise ParseError(
                "Unexpected '@.close' outside of a class block. "
                "Did you forget '@Cls.Name:' ?",
                tok,
            )

        raise ParseError(f"Unexpected token '{tok.value}'", tok)

    # ── Db block ─────────────────────────────────────────────────────────

    def _parse_db(self, at_tok: Token | None = None) -> Node:
        """Parse a Db block or save command.

        ``at_tok`` is the *optional* ``@`` token if the caller
        (``_parse_at_stmt``) already consumed it; otherwise the stream is
        expected to start with ``Db``.

            Db:              ->  DbNode(name="db")
            Db.Personal:     ->  DbNode(name="Personal")
            Db.Personal.save ->  DbSaveNode(database_name="Personal")
            body...
            db.close
        """
        if at_tok is not None:
            tok = at_tok
            self._consume(TokenType.DB, "Expected 'Db' after '@'")
        else:
            tok = self._consume(TokenType.DB, "Expected 'Db' to open a database block")

        if self._check(TokenType.DOT):
            self._advance()
            name_tok = self._consume(
                TokenType.IDENTIFIER, "Expected database name after 'Db.'",
            )
            db_name = name_tok.value
        else:
            db_name = "db"

        # Db.<name>.save  →  DbSaveNode
        # Db.<name>.load  →  DbLoadNode
        if self._check(TokenType.DOT):
            self._advance()
            cmd_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected 'save' or 'load' after '.'",
            )
            if cmd_tok.value == "save":
                return DbSaveNode(database_name=db_name, line=tok.line)
            if cmd_tok.value == "load":
                return DbLoadNode(database_name=db_name, line=tok.line)
            raise ParseError(
                f"Expected 'save' or 'load' after '.', got '{cmd_tok.value}'",
                cmd_tok,
            )

        self._consume(TokenType.COLON, "Expected ':' after database name")

        body = self._parse_body(terminators=frozenset({TokenType.DB_CLOSE}))
        has_explicit_close = self._check(TokenType.DB_CLOSE)
        if has_explicit_close:
            self._advance()

        return DbNode(name=db_name, body=body, line=tok.line, auto_close=not has_explicit_close)

    # ── Class / @-statement ──────────────────────────────────────────────

    def _parse_at_stmt(self) -> Node:
        """Parse a class definition, a Db block, or a standalone ``@`` marker.

            @Cls.Name:      ->  ClassNode
            @Db:            ->  DbNode
            @               ->  IdentifierNode("@")  (close marker)
        """
        at_tok = self._consume(TokenType.AT, "Expected '@'")
        if self._check(TokenType.CLS):
            self._advance()
            self._consume(TokenType.DOT, "Expected '.' after 'Cls'")
            name_tok = self._consume(
                TokenType.IDENTIFIER, "Expected class name after 'Cls.'",
            )
            self._consume(TokenType.COLON, "Expected ':' after class name")
            members = self._parse_class_body()
            if self._check(TokenType.AT, TokenType.AT_CLOSE):
                if self._check(TokenType.AT):
                    next_idx = self.pos + 1
                    if next_idx < len(self.tokens):
                        next_tt = self.tokens[next_idx].type
                        is_explicit = next_tt not in (TokenType.CLS, TokenType.DB)
                    else:
                        is_explicit = True
                else:  # AT_CLOSE — always explicit
                    is_explicit = True
                if is_explicit:
                    self._advance()
                return ClassNode(
                    name=name_tok.value, members=members,
                    line=at_tok.line, auto_close=not is_explicit,
                )
            return ClassNode(
                name=name_tok.value, members=members,
                line=at_tok.line, auto_close=True,
            )
        if self._check(TokenType.DB):
            return self._parse_db(at_tok)
        return IdentifierNode(name="@", line=at_tok.line)

    def _parse_class_body(self) -> list[Node]:
        """Parse the statements inside ``@Cls.Name:``.

        Stops at ``@`` or ``@.close`` (class terminator) or EOF.
        Methods, nested classes, and other statements are handled by the
        generic statement dispatch.
        """
        return self._parse_body(terminators=frozenset({TokenType.AT, TokenType.AT_CLOSE}))

    # ── Method definition ────────────────────────────────────────────────

    def _parse_method(self) -> MethodNode:
        """Parse a method definition:

            M.name:
                body...
            /.close
        """
        m_tok = self._consume(TokenType.M, "Expected 'M' for method definition")
        self._consume(TokenType.DOT, "Expected '.' after 'M'")
        name_tok = self._consume(
            TokenType.IDENTIFIER, "Expected method name after 'M.'",
        )
        self._consume(TokenType.COLON, "Expected ':' after method name")

        body = self._parse_body(terminators=frozenset({TokenType.METHOD_CLOSE}))
        has_close = self._check(TokenType.METHOD_CLOSE)
        if has_close:
            self._advance()

        return MethodNode(
            name=name_tok.value, body=body,
            line=m_tok.line, auto_close=not has_close,
        )

    # ── Object instantiation ─────────────────────────────────────────────

    _NAME_TOKENS: frozenset[TokenType] = frozenset({
        TokenType.IDENTIFIER,
        TokenType.P, TokenType.R, TokenType.AI,
        TokenType.DB_NEXT, TokenType.DB_BREAK, TokenType.DB_CLOSE,
        TokenType.S, TokenType.I, TokenType.L,
        TokenType.CLS, TokenType.OBJ, TokenType.M, TokenType.DB,
    })

    def _consume_name(self, message: str) -> Token:
        """Consume a token that can be used as a name (identifier or keyword)."""
        if self._check(*self._NAME_TOKENS):
            return self._advance()
        raise ParseError(message, self._current())

    def _parse_object(self) -> ObjectNode:
        """Parse an object instantiation:

            Obj.ClassName.VariableName
        """
        tok = self._consume(TokenType.OBJ, "Expected 'Obj' for object instantiation")
        self._consume(TokenType.DOT, "Expected '.' after 'Obj'")
        cls_tok = self._consume_name("Expected class name after 'Obj.'")
        self._consume(TokenType.DOT, "Expected '.' after class name")
        var_tok = self._consume_name("Expected variable name after class name")
        return ObjectNode(var_name=var_tok.value, class_name=cls_tok.value, line=tok.line)

    # ── Print statement ──────────────────────────────────────────────────

    def _parse_print(self) -> PrintNode:
        """Parse a print statement:

            p expression
        """
        tok = self._consume(TokenType.P, "Expected 'p'")
        if self._check(TokenType.DOT):
            self._advance()
        value = self._parse_expression()
        return PrintNode(value=value, line=tok.line)

    # ── Return statement ─────────────────────────────────────────────────

    def _parse_return(self) -> ReturnNode:
        """Parse a return statement:

            R.expression
        """
        r_tok = self._consume(TokenType.R, "Expected 'R' for return statement")
        self._consume(TokenType.DOT, "Expected '.' after 'R'")
        value = self._parse_expression()
        return ReturnNode(value=value, line=r_tok.line)

    # ── AI call ──────────────────────────────────────────────────────────

    def _parse_ai(self) -> AICallNode:
        """Parse an AI inference call:

            AI var_name = "prompt"
        """
        ai_tok = self._consume(TokenType.AI, "Expected 'AI' for AI inference call")
        var_tok = self._consume(
            TokenType.IDENTIFIER, "Expected variable name after 'AI'",
        )
        self._consume(TokenType.ASSIGN, "Expected '=' after AI variable name")
        prompt = self._parse_expression()
        return AICallNode(var_name=var_tok.value, prompt=prompt, line=ai_tok.line)

    # ── Typed assignment (S, I, L) ───────────────────────────────────────

    def _parse_typed_assignment(self) -> Node:
        """Parse a typed assignment or relation assignment:

            S name = value         ->  AssignmentNode
            S.name : value         ->  AssignmentNode
            I.age.Jey : value      ->  RelationAssignmentNode
        """
        type_tok = self._advance()

        if not self._check(TokenType.DOT):
            name_tok = self._consume(
                TokenType.IDENTIFIER,
                f"Expected identifier after '{type_tok.value}'",
            )
            if self._check(TokenType.COLON):
                self._advance()
            elif self._check(TokenType.ASSIGN):
                self._advance()
            else:
                raise ParseError(
                    f"Expected ':' or '=' after '{type_tok.value} {name_tok.value}'",
                    self._current(),
                )
            value = self._parse_expression()
            return AssignmentNode(
                var_type=type_tok.type,
                name=name_tok.value,
                value=value,
                line=type_tok.line,
            )

        parts: list[str] = []
        while self._check(TokenType.DOT):
            self._advance()
            parts.append(
                self._consume(TokenType.IDENTIFIER, "Expected identifier after '.'").value,
            )
        self._consume(TokenType.COLON, "Expected ':' after property path")
        value = self._parse_expression()

        if len(parts) == 1:
            return AssignmentNode(
                var_type=type_tok.type,
                name=parts[0],
                value=value,
                line=type_tok.line,
            )
        if len(parts) > 2:
            raise ParseError(
                "Relation assignment requires exactly one property and one entity "
                "(e.g. 'I.age.Jey : value')",
                type_tok,
            )
        return RelationAssignmentNode(
            var_type=type_tok.type,
            property_name=parts[0],
            entity_name=parts[1],
            value=value,
            line=type_tok.line,
        )

    # ── Identifier statement ─────────────────────────────────────────────

    def _parse_identifier_stmt(self) -> Node:
        """Parse a statement that starts with an identifier.

            id : expr    ->  MethodCallNode
            id = expr    ->  AssignmentNode
            id.run       ->  MethodInvokeNode
            id op expr   ->  BinaryOpNode  (other operators)
            id           ->  bare IdentifierNode
        """
        name_tok = self._advance()
        if self._check(TokenType.COLON):
            self._advance()
            value = self._parse_expression()
            return MethodCallNode(method=name_tok.value, argument=value, line=name_tok.line)
        if self._check(TokenType.ASSIGN):
            self._advance()
            value = self._parse_expression()
            return AssignmentNode(
                var_type=None,
                name=name_tok.value,
                value=value,
                line=name_tok.line,
            )
        if self._check(TokenType.DOT):
            dot_tok = self._advance()
            run_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected 'run' after '.' for method invocation",
            )
            if run_tok.value == "run":
                return MethodInvokeNode(method_name=name_tok.value, line=name_tok.line)
            raise ParseError(
                f"Expected 'run' after '.', got '{run_tok.value}'",
                run_tok,
            )
        left: Node = IdentifierNode(name=name_tok.value, line=name_tok.line)
        return self._parse_binary_rhs(left, name_tok.line)

    # ── Bang statement (!) ───────────────────────────────────────────────

    def _parse_bang_stmt(self) -> Node:
        """Parse a bang-prefixed statement.

        ``!`` is only valid as the start of an ``! If`` conditional.
        """
        bang_tok = self._advance()
        if self._check(TokenType.IDENTIFIER) and self._current().value == "If":
            return self._parse_if(bang_tok)
        raise ParseError("Expected 'If' after '!'. ", bang_tok)

    # ── If / elseif / else ───────────────────────────────────────────────

    def _parse_if(self, bang_tok: Token) -> IfNode:
        """Parse an if/elseif/else chain.

            ! If.condition,
                then_body ...
            #                       (closes then body)
            !! condition,
                elseif_body ...
            #                       (closes elseif body)
            ! Else
                else_body ...
            #                       (closes else body)
        """
        self._consume(TokenType.IDENTIFIER, "Expected 'If'")
        self._consume(TokenType.DOT, "Expected '.' after 'If'")
        condition = self._parse_expression()
        self._consume(TokenType.COMMA, "Expected ',' after If condition")

        body_terminators: frozenset[TokenType] = frozenset({
            TokenType.HASH, TokenType.BANG,
        })

        then_body = self._parse_body(terminators=body_terminators)
        has_then_close = self._check(TokenType.HASH)
        if has_then_close:
            self._advance()

        elseifs: list[ElseIfNode] = []
        else_node: Optional[ElseNode] = None

        while self._check(TokenType.BANG):
            saved_pos = self.pos
            saved_tok = self._current()
            self._advance()

            if self._check(TokenType.BANG):
                self._advance()
                elseif_cond = self._parse_expression()
                self._consume(TokenType.COMMA, "Expected ',' after ElseIf condition")
                elseif_body = self._parse_body(terminators=body_terminators)
                has_elseif_close = self._check(TokenType.HASH)
                if has_elseif_close:
                    self._advance()
                elseifs.append(ElseIfNode(
                    condition=elseif_cond,
                    body=elseif_body,
                    line=saved_tok.line,
                    auto_close=not has_elseif_close,
                ))
            elif self._check(TokenType.IDENTIFIER) and self._current().value == "Else":
                self._advance()
                else_body = self._parse_body(terminators=frozenset({TokenType.HASH}))
                has_else_close = self._check(TokenType.HASH)
                if has_else_close:
                    self._advance()
                else_node = ElseNode(
                    body=else_body,
                    line=saved_tok.line,
                    auto_close=not has_else_close,
                )
            else:
                self.pos = saved_pos
                break

        return IfNode(
            condition=condition,
            then_body=then_body,
            elseifs=elseifs,
            else_node=else_node,
            line=bang_tok.line,
            auto_close=not has_then_close,
        )

    # ── Question statement (?) ───────────────────────────────────────────

    def _parse_question_stmt(self) -> Node:
        """Parse a question-prefixed loop statement.

            ? For.var=start;end, body #   ->  ForNode
            ? While.condition, body #     ->  WhileNode
        """
        q_tok = self._advance()
        if self._check(TokenType.IDENTIFIER):
            if self._current().value == "For":
                return self._parse_for(q_tok)
            if self._current().value == "While":
                return self._parse_while(q_tok)
        raise ParseError(
            "Expected 'For' or 'While' after '?'",
            q_tok,
        )

    # ── For loop ─────────────────────────────────────────────────────────

    def _parse_for(self, q_tok: Token) -> ForNode:
        """Parse a for loop:

            ? For.var=start;end,
                body ...
            #
        """
        self._advance()
        self._consume(TokenType.DOT, "Expected '.' after 'For'")
        var_tok = self._consume(
            TokenType.IDENTIFIER, "Expected loop variable after 'For.'",
        )
        self._consume(TokenType.ASSIGN, "Expected '=' for range start")

        # Parse start expression (stop at ; which is the range separator)
        left = self._parse_primary_chain()
        while self._check(*{t for t in self._BINARY_OPS if t != TokenType.SEMICOLON}):
            op_tok = self._advance()
            right = self._parse_primary_chain()
            left = BinaryOpNode(
                operator=op_tok.value, left=left, right=right, line=op_tok.line,
            )

        # Consume ; range separator and parse end expression
        self._consume(TokenType.SEMICOLON, "Expected ';' between range start and end")
        end = self._parse_expression()
        iterable = BinaryOpNode(operator=";", left=left, right=end, line=left.line)

        self._consume(TokenType.COMMA, "Expected ',' after for clause")

        body = self._parse_body(terminators=frozenset({TokenType.HASH}))
        has_close = self._check(TokenType.HASH)
        if has_close:
            self._advance()

        return ForNode(
            variable=var_tok.value, iterable=iterable, body=body,
            line=q_tok.line, auto_close=not has_close,
        )

    # ── While loop ───────────────────────────────────────────────────────

    def _parse_while(self, q_tok: Token) -> WhileNode:
        """Parse a while loop:

            ? While.condition,
                body ...
            #
        """
        self._advance()
        self._consume(TokenType.DOT, "Expected '.' after 'While'")
        condition = self._parse_expression()
        self._consume(TokenType.COMMA, "Expected ',' after While condition")
        body = self._parse_body(terminators=frozenset({TokenType.HASH}))
        has_close = self._check(TokenType.HASH)
        if has_close:
            self._advance()

        return WhileNode(
            condition=condition, body=body,
            line=q_tok.line, auto_close=not has_close,
        )

    # ── Expression parsing ───────────────────────────────────────────────

    _BINARY_OPS: frozenset[TokenType] = frozenset({
        TokenType.EQ,    TokenType.NEQ,
        TokenType.GT,    TokenType.LT,   TokenType.GTE, TokenType.LTE,
        TokenType.PLUS,  TokenType.MINUS,
        TokenType.STAR,  TokenType.PERCENT,
        TokenType.SEMICOLON,
    })

    def _parse_primary_chain(self) -> Node:
        """Parse a primary expression followed by zero or more property accesses.

            primary ( '.' ident )*
        """
        left = self._parse_primary()
        while self._check(TokenType.DOT):
            dot_tok = self._advance()
            prop = self._consume(
                TokenType.IDENTIFIER, "Expected property name after '.'",
            )
            left = PropertyAccessNode(
                object=left, property=prop.value, line=dot_tok.line,
            )
        return left

    def _parse_expression(self) -> Node:
        """Parse an expression:

            primary ( '.' ident )* ( binary_op primary ( '.' ident )* )*
        """
        left = self._parse_primary_chain()
        return self._parse_binary_rhs(left, left.line)

    def _parse_binary_rhs(self, left: Node, line: int) -> Node:
        """Extend *left* with zero or more binary operators (left-associative).

        All operators share the same precedence.
        The right-hand side of each operator supports property access chains.
        """
        while self._check(*self._BINARY_OPS):
            op_tok = self._advance()
            right = self._parse_primary_chain()
            left = BinaryOpNode(
                operator=op_tok.value,
                left=left,
                right=right,
                line=op_tok.line,
            )
        return left

    def _parse_primary(self) -> Node:
        """Parse a primary expression: a string, integer, or identifier."""
        tok = self._current()
        if tok.type == TokenType.STRING:
            self._advance()
            return LiteralNode(value=tok.value, kind=TokenType.STRING, line=tok.line)
        if tok.type == TokenType.INTEGER:
            self._advance()
            return LiteralNode(value=tok.value, kind=TokenType.INTEGER, line=tok.line)
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentifierNode(name=tok.value, line=tok.line)
        raise ParseError(
            f"Expected a value (string, number, or identifier), "
            f"but found '{tok.value}'",
            tok,
        )
