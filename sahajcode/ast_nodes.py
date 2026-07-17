"""
SahajCode AST Node Definitions
Defines the Abstract Syntax Tree structure for the SahajCode language.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class NodeType(Enum):
    PROGRAM = 'program'
    VAR_DECL = 'var_decl'
    ASSIGNMENT = 'assignment'
    PRINT = 'print'
    INPUT = 'input'
    IF = 'if'
    WHILE = 'while'
    FOR = 'for'
    BINARY_OP = 'binary_op'
    UNARY_OP = 'unary_op'
    NUMBER = 'number'
    STRING = 'string'
    IDENTIFIER = 'identifier'
    COMMENT = 'comment'


@dataclass
class ASTNode:
    """Base AST node."""
    node_type: NodeType
    line: int = 0
    
    def __repr__(self):
        return f"{self.node_type.value}"


@dataclass
class Program(ASTNode):
    """Root node containing all statements."""
    statements: List['ASTNode'] = field(default_factory=list)


@dataclass
class VarDecl(ASTNode):
    """Variable declaration: rakha x = expr"""
    name: str = ""
    value: Optional[ASTNode] = None


@dataclass
class Assignment(ASTNode):
    """Variable reassignment: x = expr"""
    name: str = ""
    value: Optional[ASTNode] = None


@dataclass
class Print(ASTNode):
    """Output statement: bhana expr"""
    expr: Optional[ASTNode] = None


@dataclass
class Input(ASTNode):
    """Input statement: suna identifier"""
    name: str = ""


@dataclass
class If(ASTNode):
    """If statement: yedi expr bhane ... [natra ...] antya"""
    condition: Optional[ASTNode] = None
    then_branch: List[ASTNode] = field(default_factory=list)
    else_branch: List[ASTNode] = field(default_factory=list)


@dataclass  
class While(ASTNode):
    """While loop: jaba expr samma ... antya"""
    condition: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class For(ASTNode):
    """For loop: guma var = start dekhi end ... antya"""
    var: str = ""
    start: Optional[ASTNode] = None
    end: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class BinaryOp(ASTNode):
    """Binary operation: left op right"""
    op: str = ""
    left: Optional[ASTNode] = None
    right: Optional[ASTNode] = None


@dataclass
class UnaryOp(ASTNode):
    """Unary operation: op operand"""
    op: str = ""
    operand: Optional[ASTNode] = None


@dataclass
class Number(ASTNode):
    """Integer literal"""
    value: int = 0


@dataclass
class String(ASTNode):
    """String literal"""
    value: str = ""


@dataclass
class Identifier(ASTNode):
    """Variable reference"""
    name: str = ""


@dataclass
class Comment(ASTNode):
    """Comment node (preserved for source mapping)"""
    text: str = ""
