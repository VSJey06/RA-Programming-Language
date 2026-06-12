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
                   | RunBlock | FunBlock

    RunBlock     := '.run:' {stmt} 'r.close'
    FunBlock     := '.fun:' {stmt} 'f.close'

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
        Run block   :  r.close
        Fun block   :  f.close
        Class       :  @  (or @.close)
        Method      :  /  (or /.close)
        If / ElseIf :  #
        For / While :  #
"""

from __future__ import annotations

from typing import Optional

from lexer.tokens import Token, TokenType
from source_location import SourceLocation
from parser.ra_ast import (
    AICallNode,
    AINode,
    AssignmentNode,
    BinaryOpNode,
    BooleanNode,
    CallBlockNode,
    CaseNode,
    CheckNode,
    ClassNode,
    ConstructorNode,
    CovBlockNode,
    DbBreakNode,
    DbLoadNode,
    DbNextNode,
    DbNode,
    DbSaveNode,
    ElseIfNode,
    ElseNode,
    EncapsulationNode,
    ExpoBlockNode,
    ForNode,
    FunctionBlockNode,
    GenerateNode,
    FunctionFlowNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    MethodCallNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    ObjectNode,
    OOPNode,
    PFNode,
    PrintNode,
    ProgramHandlerNode,
    ProgramNode,
    PropertyAccessNode,
    PropertyAssignmentNode,
    RelationAssignmentNode,
    ReturnNode,
    RunBlockNode,
    SwitchNode,
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
        self.message = message
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
        self._in_ff_flow = False

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

    # ── Source-location helpers ─────────────────────────────────────────

    @staticmethod
    def _loc(node: Node, token: Token) -> Node:
        """Populate *node* with column/end positions from *token* and return it."""
        node.col = token.column
        node.end_line = token.end_line
        node.end_column = token.end_column
        return node

    @staticmethod
    def _loc_range(
        node: Node,
        start_token: Token,
        end_token: Token | None = None,
    ) -> Node:
        """Populate *node* with location spanning *start_token* … *end_token*."""
        node.col = start_token.column
        node.end_line = end_token.end_line if end_token else start_token.end_line
        node.end_column = end_token.end_column if end_token else start_token.end_column
        return node

    # ── Main entry point ─────────────────────────────────────────────────

    def parse(self) -> ProgramNode:
        """Parse the full token stream into a ``ProgramNode``."""
        body: list[Node] = []
        first_tok = self._current()
        while not self._check(TokenType.EOF):
            stmt = self._parse_stmt()
            if stmt is not None:
                body.append(stmt)
        node = ProgramNode(line=first_tok.line, body=body)
        eof_tok = self._current()
        return self._loc_range(node, first_tok, eof_tok)

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
        if tt == TokenType.PL:
            return self._parse_print_line()
        if tt == TokenType.R:
            return self._parse_return()
        if tt == TokenType.AI:
            if (self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER
                    and self.pos + 2 < len(self.tokens)
                    and self.tokens[self.pos + 2].type == TokenType.ASSIGN):
                return self._parse_ai()
            self._advance()
            return AINode(line=tok.line)
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

        if tt == TokenType.OOP:
            self._advance()
            return OOPNode(line=tok.line)

        if tt == TokenType.PF:
            self._advance()
            return PFNode(line=tok.line)

        if tt == TokenType.PH:
            return self._parse_ph()

        if tt == TokenType.FF:
            return self._parse_ff()

        if tt == TokenType.CON:
            return self._parse_constructor()

        if tt == TokenType.EN:
            return self._parse_encapsulation()

        if tt == TokenType.DOT:
            return self._parse_dot_stmt()

        if tt == TokenType.RUN_CLOSE:
            raise ParseError(
                "Unexpected 'r.close' outside of a .run: block. "
                "Did you forget '.run:' ?",
                tok,
            )

        if tt == TokenType.FUN_CLOSE:
            raise ParseError(
                "Unexpected 'f.close' outside of a .fun: or fF: block. "
                "Did you forget '.fun:' or 'fF:' ?",
                tok,
            )

        if tt == TokenType.CON_CLOSE:
            raise ParseError(
                "Unexpected 'con.close' outside of a constructor block. "
                "Did you forget 'Con:' ?",
                tok,
            )

        if tt == TokenType.CHECK:
            return self._parse_check()

        if tt == TokenType.KEY:
            return self._parse_key()

        if tt == TokenType.EN_CLOSE:
            raise ParseError(
                "Unexpected 'en.close' outside of an encapsulation block. "
                "Did you forget 'En:' ?",
                tok,
            )

        if tt == TokenType.AT_CLOSE:
            raise ParseError(
                "Unexpected '@.close' outside of a class block. "
                "Did you forget '@Cls.Name:' ?",
                tok,
            )

        if tt == TokenType.CHECK_CLOSE:
            raise ParseError(
                "Unexpected 'Check.close' outside of a Check block. "
                "Did you forget 'Check:' ?",
                tok,
            )

        if tt == TokenType.KEY_CLOSE:
            raise ParseError(
                "Unexpected 'Key.close' outside of a Key block. "
                "Did you forget 'Key.value:' ?",
                tok,
            )

        if tt == TokenType.PH_CLOSE:
            raise ParseError(
                "Unexpected 'pH.close' outside of a pH block. "
                "Did you forget 'pH:' ?",
                tok,
            )

        if tt == TokenType.COV_CLOSE:
            raise ParseError(
                "Unexpected 'cov.close' outside of a .cov: block. "
                "Did you forget '.cov:' ?",
                tok,
            )

        if tt == TokenType.EXPO_CLOSE:
            raise ParseError(
                "Unexpected 'ex.close' outside of a .expo: block. "
                "Did you forget '.expo:' ?",
                tok,
            )

        if tt == TokenType.CALL_CLOSE:
            raise ParseError(
                "Unexpected 'call.close' outside of a .Call: block. "
                "Did you forget '.Call:' ?",
                tok,
            )

        if tt == TokenType.GEN_CLOSE:
            raise ParseError(
                "Unexpected 'gen.close' outside of a .Gen: block. "
                "Did you forget '.Gen:' ?",
                tok,
            )

        raise ParseError(f"Unexpected token '{tok.value}'", tok)

    # ── Dot-prefixed statements (.run:) ──────────────────────────────────

    def _parse_dot_stmt(self) -> Node:
        """Parse a statement that starts with '.'.

        Supported forms: ``.run:``, ``.fun:``, ``.cov:``, ``.expo:``,
        ``.Call:`` and ``.Gen:``.
        """
        dot_tok = self._advance()  # consume '.'
        if (self._check(TokenType.IDENTIFIER)
                and self._current().value in ("run", "fun", "cov", "expo", "Call", "Gen")
                and self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TokenType.COLON):
            kind = self._advance().value  # consume identifier
            self._advance()  # consume ':'
            if kind == "run":
                return self._parse_run_block(dot_tok)
            if kind == "fun":
                return self._parse_function_block(dot_tok)
            if kind == "cov":
                return self._parse_cov_block(dot_tok)
            if kind == "expo":
                return self._parse_expo_block(dot_tok)
            if kind == "Gen":
                return self._parse_gen_block(dot_tok)
            return self._parse_call_block(dot_tok)
        raise ParseError(
            "Expected '.run:', '.fun:', '.cov:', '.expo:', '.Call:' or '.Gen:'",
            dot_tok,
        )

    def _parse_run_block(self, dot_tok: Token) -> RunBlockNode:
        """Parse an immediate execution block:

            .run:
                body...
            r.close
        """
        body = self._parse_body(terminators=frozenset({TokenType.RUN_CLOSE}))
        has_close = self._check(TokenType.RUN_CLOSE)
        if has_close:
            self._advance()
        return RunBlockNode(
            body=body,
            line=dot_tok.line,
            auto_close=not has_close,
        )

    def _parse_function_block(self, dot_tok: Token) -> FunctionBlockNode:
        """Parse a local-scope function block:

            .fun:
                body...
            f.close
        """
        body = self._parse_body(terminators=frozenset({TokenType.FUN_CLOSE}))
        has_close = self._check(TokenType.FUN_CLOSE)
        if has_close:
            self._advance()
        return FunctionBlockNode(
            body=body,
            line=dot_tok.line,
            auto_close=not has_close,
        )

    def _parse_cov_block(self, dot_tok: Token) -> CovBlockNode:
        """Parse an AI coverage block:

            .cov: <language>."<path>" cov.close
        """
        lang_tok = self._consume(
            TokenType.IDENTIFIER,
            "Expected language name after '.cov:'",
        )
        self._consume(TokenType.DOT, "Expected '.' after language name")
        path_tok = self._consume(
            TokenType.STRING,
            "Expected file path string after '.'",
        )
        has_close = self._check(TokenType.COV_CLOSE)
        if has_close:
            self._advance()
        return CovBlockNode(
            language=lang_tok.value,
            path=path_tok.value,
            line=dot_tok.line,
        )

    def _parse_expo_block(self, dot_tok: Token) -> ExpoBlockNode:
        """Parse an AI export block:

            .expo: <language>."<path>" ex.close
        """
        lang_tok = self._consume(
            TokenType.IDENTIFIER,
            "Expected language name after '.expo:'",
        )
        self._consume(TokenType.DOT, "Expected '.' after language name")
        path_tok = self._consume(
            TokenType.STRING,
            "Expected file path string after '.'",
        )
        has_close = self._check(TokenType.EXPO_CLOSE)
        if has_close:
            self._advance()
        return ExpoBlockNode(
            language=lang_tok.value,
            path=path_tok.value,
            line=dot_tok.line,
        )

    def _parse_call_block(self, dot_tok: Token) -> CallBlockNode:
        """Parse an AI call block:

            .Call:"<question>" call.close
        """
        question_tok = self._consume(
            TokenType.STRING,
            "Expected question string after '.Call:'",
        )
        has_close = self._check(TokenType.CALL_CLOSE)
        if has_close:
            self._advance()
        return CallBlockNode(
            question=question_tok.value,
            line=dot_tok.line,
        )

    def _parse_gen_block(self, dot_tok: Token) -> GenerateNode:
        """Parse an AI generation block:

            .Gen:"<description>" gen.close
        """
        desc_tok = self._consume(
            TokenType.STRING,
            "Expected description string after '.Gen:'",
        )
        has_close = self._check(TokenType.GEN_CLOSE)
        if has_close:
            self._advance()
        return GenerateNode(
            description=desc_tok.value,
            line=dot_tok.line,
        )

    # ── Check / Valid / Invalid block ───────────────────────────────────

    def _parse_check(self) -> CheckNode:
        """Parse an error-handling block:

            Check:
                statements…
            Valid:
                statements…
            Invalid:
                statements…
            Check.close
        """
        tok = self._consume(TokenType.CHECK, "Expected 'Check'")
        self._consume(TokenType.COLON, "Expected ':' after 'Check'")

        body = self._parse_body(terminators=frozenset({
            TokenType.VALID, TokenType.INVALID, TokenType.CHECK_CLOSE,
        }))

        valid_body: list[Node] = []
        if self._check(TokenType.VALID):
            self._advance()
            self._consume(TokenType.COLON, "Expected ':' after 'Valid'")
            valid_body = self._parse_body(terminators=frozenset({
                TokenType.INVALID, TokenType.CHECK_CLOSE,
            }))

        invalid_body: list[Node] = []
        if self._check(TokenType.INVALID):
            self._advance()
            self._consume(TokenType.COLON, "Expected ':' after 'Invalid'")
            invalid_body = self._parse_body(terminators=frozenset({
                TokenType.CHECK_CLOSE,
            }))

        has_close = self._check(TokenType.CHECK_CLOSE)
        if has_close:
            self._advance()

        return CheckNode(
            body=body,
            valid_body=valid_body,
            invalid_body=invalid_body,
            line=tok.line,
            auto_close=not has_close,
        )

    # ── Key / case / def (switch) block ─────────────────────────────────

    def _parse_key(self) -> SwitchNode:
        """Parse a switch block:

            Key.value:
                c.condition:
                    statements…
                c.condition:
                    statements…
                def:
                    statements…
            Key.close
        """
        key_tok = self._consume(TokenType.KEY, "Expected 'Key'")
        self._consume(TokenType.DOT, "Expected '.' after 'Key'")
        value = self._parse_expression()
        self._consume(TokenType.COLON, "Expected ':' after Key value")

        cases: list[CaseNode] = []
        default_body: list[Node] = []

        while not self._check(TokenType.KEY_CLOSE, TokenType.EOF):
            # Check for 'def:' (default case)
            if self._check(TokenType.IDENTIFIER) and self._current().value == "def":
                nxt = self.pos + 1
                if nxt < len(self.tokens) and self.tokens[nxt].type == TokenType.COLON:
                    self._advance()  # consume 'def'
                    self._advance()  # consume ':'
                    default_body = self._parse_body(terminators=frozenset({
                        TokenType.KEY_CLOSE,
                    }))
                    break

            # Check for 'c.condition:' (case)
            if self._check(TokenType.IDENTIFIER) and self._current().value == "c":
                nxt = self.pos + 1
                if nxt < len(self.tokens) and self.tokens[nxt].type == TokenType.DOT:
                    c_tok = self._advance()  # consume 'c'
                    self._advance()  # consume '.'
                    condition = self._parse_expression()
                    self._consume(
                        TokenType.COLON,
                        "Expected ':' after case condition",
                    )
                    case_body = self._parse_key_case_body()
                    cases.append(CaseNode(
                        condition=condition, body=case_body, line=c_tok.line,
                    ))
                    continue

            raise ParseError(
                "Expected case ('c.condition:') or default ('def:') "
                "in Key block",
                self._current(),
            )

        has_close = self._check(TokenType.KEY_CLOSE)
        if has_close:
            self._advance()

        return SwitchNode(
            value=value,
            cases=cases,
            default_body=default_body,
            line=key_tok.line,
            auto_close=not has_close,
        )

    def _parse_key_case_body(self) -> list[Node]:
        """Parse the body of a case inside a Key block.

        Stops at the next ``c.``, ``def:``, or ``Key.close``.
        """
        body: list[Node] = []
        while not self._check(TokenType.EOF):
            if self._check(TokenType.KEY_CLOSE):
                break
            if self._check(TokenType.IDENTIFIER):
                val = self._current().value
                nxt = self.pos + 1
                if nxt < len(self.tokens):
                    nxt_tt = self.tokens[nxt].type
                    if val == "c" and nxt_tt == TokenType.DOT:
                        break
                    if val == "def" and nxt_tt == TokenType.COLON:
                        break
            stmt = self._parse_stmt()
            if stmt is not None:
                body.append(stmt)
        return body

    # ── Program Handler (pH) block ──────────────────────────────────────

    def _parse_ph(self) -> ProgramHandlerNode:
        """Parse a Program Handler block:

            pH:
                @Cls.Name
                Obj.Class.Var
                M.Name
            pH.close
        """
        tok = self._consume(TokenType.PH, "Expected 'pH'")
        self._consume(TokenType.COLON, "Expected ':' after 'pH'")

        body: list[Node] = []
        while not self._check(TokenType.PH_CLOSE, TokenType.EOF):
            item = self._parse_ph_item()
            if item is not None:
                body.append(item)

        has_close = self._check(TokenType.PH_CLOSE)
        if has_close:
            self._advance()

        return ProgramHandlerNode(
            body=body, line=tok.line, auto_close=not has_close,
        )

    def _parse_ph_item(self) -> Optional[Node]:
        """Parse a single entry inside a pH block.

        Supported forms:

            @Cls.Name       ->  ClassNode (reference only)
            Obj.Cls.Var     ->  ObjectNode
            M.Name          ->  MethodNode (reference only)
        """
        # Detect .run: or .fun: and reject
        if (self._check(TokenType.DOT)
                and self.pos + 2 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER
                and self.tokens[self.pos + 1].value in ("run", "fun")
                and self.tokens[self.pos + 2].type == TokenType.COLON):
            raise ParseError(
                ".run and .fun are not allowed inside pH blocks",
                self._current(),
            )

        tok = self._current()
        tt  = tok.type

        if tt == TokenType.AT:
            self._advance()
            self._consume(TokenType.CLS, "Expected 'Cls' after '@' in pH block")
            self._consume(TokenType.DOT, "Expected '.' after 'Cls' in pH block")
            name_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected class name after 'Cls.' in pH block",
            )
            return ClassNode(name=name_tok.value, line=tok.line, members=[])

        if tt == TokenType.OBJ:
            self._advance()
            self._consume(TokenType.DOT, "Expected '.' after 'Obj' in pH block")
            cls_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected class name after 'Obj.' in pH block",
            )
            self._consume(
                TokenType.DOT,
                "Expected '.' after class name in pH block",
            )
            var_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected variable name in pH block",
            )
            return ObjectNode(
                var_name=var_tok.value, class_name=cls_tok.value, line=tok.line,
            )

        if tt == TokenType.M:
            self._advance()
            self._consume(TokenType.DOT, "Expected '.' after 'M' in pH block")
            name_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected method name after 'M.' in pH block",
            )
            return MethodNode(name=name_tok.value, line=tok.line, body=[])

        raise ParseError(
            "Expected '@Cls.', 'Obj.', or 'M.' in pH block",
            tok,
        )

    # ── Function Flow (fF) block ────────────────────────────────────────

    def _parse_ff(self) -> FunctionFlowNode:
        """Parse a Function Flow block:

        Mode A (unbound):
            fF:
                Object.Method
            f.close

        Mode B (explicit target):
            fF.M.Login:
                User.Validate
                User.Login
            f.close
        """
        tok = self._consume(TokenType.FF, "Expected 'fF'")

        # Detect Mode B: fF.<target>:
        target: str | None = None
        if self._check(TokenType.DOT):
            self._advance()  # consume '.'
            parts: list[str] = []
            while not self._check(TokenType.COLON, TokenType.EOF):
                t = self._current()
                if t.type == TokenType.AT:
                    parts.append("@")
                    self._advance()
                elif t.type == TokenType.DOT:
                    parts.append(".")
                    self._advance()
                else:
                    parts.append(str(t.value))
                    self._advance()
            target = "".join(parts)

        self._consume(TokenType.COLON, "Expected ':' after 'fF'")

        body: list[Node] = []
        saved_in_ff = self._in_ff_flow
        self._in_ff_flow = True
        try:
            while not self._check(TokenType.FUN_CLOSE, TokenType.EOF):
                item = self._parse_ff_item()
                if item is not None:
                    body.append(item)
        finally:
            self._in_ff_flow = saved_in_ff

        has_close = self._check(TokenType.FUN_CLOSE)
        if has_close:
            self._advance()

        return FunctionFlowNode(
            body=body, line=tok.line, auto_close=not has_close, target=target,
        )

    def _parse_ff_item(self) -> Optional[Node]:
        """Parse a single entry inside an fF block.

        Supported forms:

            Object.Method       ->  MethodInvokeNode
            Check: … Check.close  ->  CheckNode
            Key.expr: … Key.close ->  SwitchNode

        Raises a clear error for .run: inside fF.
        """
        # Detect .run: or .fun: and reject
        if (self._check(TokenType.DOT)
                and self.pos + 2 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER
                and self.tokens[self.pos + 1].value in ("run", "fun")
                and self.tokens[self.pos + 2].type == TokenType.COLON):
            raise ParseError(
                ".run and .fun are not allowed inside fF blocks",
                self._current(),
            )

        # Check / Key blocks inside fF
        if self._check(TokenType.CHECK):
            return self._parse_check()
        if self._check(TokenType.KEY):
            return self._parse_key()

        # Object.Method (default)
        obj_tok = self._consume(
            TokenType.IDENTIFIER,
            "Expected object name in fF block",
        )
        self._consume(TokenType.DOT, "Expected '.' after object name in fF block")
        method_tok = self._consume(
            TokenType.IDENTIFIER,
            "Expected method name after '.' in fF block",
        )
        return MethodInvokeNode(
            method_name=method_tok.value,
            object_name=obj_tok.value,
            line=obj_tok.line,
        )

    # ── OOP block constructors ─────────────────────────────────────────

    def _parse_constructor(self) -> ConstructorNode:
        """Parse a constructor block:

            Con:
                statements...
            con.close
        """
        tok = self._consume(TokenType.CON, "Expected 'Con'")
        self._consume(TokenType.COLON, "Expected ':' after 'Con'")
        body = self._parse_body(terminators=frozenset({TokenType.CON_CLOSE}))
        has_close = self._check(TokenType.CON_CLOSE)
        if has_close:
            self._advance()
        return ConstructorNode(
            body=body,
            line=tok.line,
            auto_close=not has_close,
        )

    def _parse_encapsulation(self) -> EncapsulationNode:
        """Parse an encapsulation block:

            En:
                properties...
            en.close
        """
        tok = self._consume(TokenType.EN, "Expected 'En'")
        self._consume(TokenType.COLON, "Expected ':' after 'En'")
        body = self._parse_body(terminators=frozenset({TokenType.EN_CLOSE}))
        has_close = self._check(TokenType.EN_CLOSE)
        if has_close:
            self._advance()
        return EncapsulationNode(
            body=body,
            line=tok.line,
            auto_close=not has_close,
        )

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
        TokenType.BOOLEAN_TF,
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
        """Parse a print-with-newline statement:

            p expression
            p.expression
        """
        tok = self._consume(TokenType.P, "Expected 'p'")
        if self._check(TokenType.DOT):
            self._advance()
        value = self._parse_expression()
        return PrintNode(value=value, line=tok.line, no_newline=False)

    def _parse_print_line(self) -> PrintNode:
        """Parse a print-without-newline statement:

            pl expression
            pl.expression
        """
        tok = self._consume(TokenType.PL, "Expected 'pl'")
        if self._check(TokenType.DOT):
            self._advance()
        value = self._parse_expression()
        return PrintNode(value=value, line=tok.line, no_newline=True)

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
                value = self._parse_expression()
            elif self._check(TokenType.ASSIGN):
                self._advance()
                value = self._parse_expression()
            else:
                if type_tok.type == TokenType.I:
                    value = LiteralNode(value=0, kind=TokenType.INTEGER, line=type_tok.line)
                else:
                    value = LiteralNode(value=None, kind=TokenType.STRING, line=type_tok.line)
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
            next_tok = self._consume(
                TokenType.IDENTIFIER,
                "Expected identifier after '.'",
            )
            # Global method: name.run
            if next_tok.value == "run":
                return MethodInvokeNode(
                    method_name=name_tok.value, line=name_tok.line,
                )
            # Stack / property operation: name.prop:expr  (e.g. Users.push:10)
            if self._check(TokenType.COLON):
                self._advance()
                arg = self._parse_expression()
                return MethodCallNode(
                    method=f"{name_tok.value}.{next_tok.value}",
                    argument=arg, line=name_tok.line,
                )
            # Property chain: name.prop.subprop / name.prop.N / name.diagonal.x-y
            prop_parts: list[str] = [next_tok.value]
            while self._check(TokenType.DOT):
                self._advance()
                # Coordinate syntax: name.prop.X,Y or name.prop.X,Y:expr
                if (self._current().type in (TokenType.INTEGER, TokenType.IDENTIFIER)
                        and self.pos + 1 < len(self.tokens)
                        and self.tokens[self.pos + 1].type == TokenType.COMMA):
                    x_tok = self._advance()
                    self._consume(TokenType.COMMA, "Expected ',' after coordinate X")
                    y_tok = self._advance()
                    coord = f"{x_tok.value},{y_tok.value}"
                    prop_parts.append(coord)
                    if self._check(TokenType.COLON):
                        self._advance()
                        arg = self._parse_expression()
                        return MethodCallNode(
                            method=f"{name_tok.value}.{'.'.join(prop_parts)}",
                            argument=arg, line=name_tok.line,
                        )
                    continue
                sub_prop = self._parse_dot_property()
                # Check for special .run termination
                if sub_prop == "run" and len(prop_parts) == 1:
                    return MethodInvokeNode(
                        method_name=prop_parts[0],
                        object_name=name_tok.value,
                        line=name_tok.line,
                    )
                prop_parts.append(sub_prop)
                if self._check(TokenType.COLON):
                    self._advance()
                    arg = self._parse_expression()
                    return MethodCallNode(
                        method=f"{name_tok.value}.{'.'.join(prop_parts)}",
                        argument=arg, line=name_tok.line,
                    )
            if self._in_ff_flow and len(prop_parts) == 1:
                return MethodInvokeNode(
                    method_name=prop_parts[0],
                    object_name=name_tok.value,
                    line=name_tok.line,
                )
            return PropertyAccessNode(
                object=IdentifierNode(name=name_tok.value, line=name_tok.line),
                property=".".join(prop_parts),
                line=dot_tok.line,
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

    def _parse_dot_property(self) -> str:
        """Parse property name after '.' and return it as a string.

        Handles:
        - ``IDENTIFIER``           → ``"x"``
        - ``IDENTIFIER - IDENTIFIER`` → ``"x-y"``
        - ``- IDENTIFIER``         → ``"-x"``
        - ``- IDENTIFIER - IDENTIFIER`` → ``"-x-y"``
        - ``INTEGER``              → ``"3"``
        """
        tok = self._current()

        # Negative prefix: .-x, .-x-y
        if tok.type == TokenType.MINUS:
            self._advance()
            first = self._consume(
                TokenType.IDENTIFIER, "Expected identifier after '-.'",
            )
            prop = "-" + first.value
            if (self._check(TokenType.MINUS)
                    and self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER):
                self._advance()
                second = self._advance()
                prop += "-" + second.value
            return prop

        # Integer property: .N (row.3, colm.5)
        if tok.type == TokenType.INTEGER:
            self._advance()
            return str(tok.value)

        # Regular identifier property, possibly compound
        if tok.type == TokenType.IDENTIFIER:
            prop_tok = self._advance()
            prop = prop_tok.value
            if (self._check(TokenType.MINUS)
                    and self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER):
                self._advance()
                second = self._advance()
                prop += "-" + second.value
            return prop

        raise ParseError("Expected property name after '.'", tok)

    def _parse_primary_chain(self) -> Node:
        """Parse a primary expression followed by zero or more property accesses.

            primary ( '.' ident )*

        Stops before a DOT that introduces a ``.fun:`` or ``.run:`` block
        (DOT + IDENTIFIER("fun"/"run") + COLON) so the statement-level
        dispatcher can handle those constructs.
        """
        left = self._parse_primary()
        while self._check(TokenType.DOT):
            # Peek ahead: if DOT + IDENTIFIER("fun"/"run") + COLON, this is a
            # .fun: / .run: statement, not a property access.
            nxt = self.pos + 1
            if (nxt < len(self.tokens)
                    and self.tokens[nxt].type == TokenType.IDENTIFIER
                    and self.tokens[nxt].value in ("fun", "run")
                    and nxt + 1 < len(self.tokens)
                    and self.tokens[nxt + 1].type == TokenType.COLON):
                break
            dot_tok = self._advance()
            # Coordinate syntax: .INTEGER,INTEGER appended to last property
            if (self._current().type in (TokenType.INTEGER, TokenType.IDENTIFIER)
                    and self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.COMMA):
                x_tok = self._advance()
                self._consume(TokenType.COMMA, "Expected ',' after coordinate X")
                y_tok = self._advance()
                coord = f"{x_tok.value},{y_tok.value}"
                if isinstance(left, PropertyAccessNode):
                    left = PropertyAccessNode(
                        object=left.object,
                        property=f"{left.property}.{coord}",
                        line=dot_tok.line,
                    )
                else:
                    left = PropertyAccessNode(
                        object=left, property=coord,
                        line=dot_tok.line,
                    )
            else:
                prop = self._parse_dot_property()
                left = PropertyAccessNode(
                    object=left, property=prop, line=dot_tok.line,
                )
        return left

    def _parse_expression(self) -> Node:
        """Parse an expression:

            primary ( '.' ident )* ( binary_op primary ( '.' ident )* )*
            optionally followed by .TF boolean suffix
        """
        left = self._parse_primary_chain()
        left = self._parse_binary_rhs(left, left.line)
        if self._check(TokenType.BOOLEAN_TF):
            self._advance()
            left = BooleanNode(expr=left, line=left.line)
        return left

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
        """Parse a primary expression: string, integer, float, or identifier."""
        tok = self._current()
        if tok.type == TokenType.STRING:
            self._advance()
            return LiteralNode(value=tok.value, kind=TokenType.STRING, line=tok.line)
        if tok.type == TokenType.INTEGER:
            self._advance()
            return LiteralNode(value=tok.value, kind=TokenType.INTEGER, line=tok.line)
        if tok.type == TokenType.FLOAT:
            self._advance()
            return LiteralNode(value=tok.value, kind=TokenType.FLOAT, line=tok.line)
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentifierNode(name=tok.value, line=tok.line)
        raise ParseError(
            f"Expected a value (string, number, or identifier), "
            f"but found '{tok.value}'",
            tok,
        )
