"""
SahajCode Symbol Table
Tracks variable names, types, and scope during parsing and code generation.
"""

from typing import Dict, Optional, List, Tuple
from enum import Enum
from .ast_nodes import NodeType


class VarType(Enum):
    INT = 'int'
    STRING = 'string'


class Symbol:
    """Represents a variable symbol."""
    def __init__(self, name: str, var_type: VarType, line_declared: int, is_initialized: bool = False):
        self.name = name
        self.type = var_type
        self.line_declared = line_declared
        self.is_initialized = is_initialized
    
    def __repr__(self):
        return f"Symbol({self.name}: {self.type.value})"


class SymbolTable:
    """Global scope symbol table for SahajCode MVP."""
    
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.inputs_pending: List[Tuple[str, int]] = []  # Variables from suna that need declaration
    
    def declare(self, name: str, var_type: VarType, line: int) -> Optional[str]:
        """Declare a variable. Returns error message if redeclaration."""
        if name in self.symbols:
            return f"'{name}' पहिले नै परिभाषित भएको छ"
        self.symbols[name] = Symbol(name, var_type, line, is_initialized=True)
        return None
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a variable."""
        return self.symbols.get(name)
    
    def ensure_declared(self, name: str, line: int) -> Optional[str]:
        """Check if variable is declared. Returns error if not."""
        if name not in self.symbols:
            return f"'{name}' परिभाषित भएको छैन"
        return None
    
    def infer_type(self, expr_node) -> VarType:
        """Infer type from an expression node."""
        from .ast_nodes import NodeType
        
        if expr_node.node_type == NodeType.NUMBER:
            return VarType.INT
        elif expr_node.node_type == NodeType.STRING:
            return VarType.STRING
        elif expr_node.node_type == NodeType.IDENTIFIER:
            sym = self.lookup(expr_node.name)
            return sym.type if sym else VarType.INT
        elif expr_node.node_type in [NodeType.BINARY_OP, NodeType.UNARY_OP]:
            return VarType.INT
        return VarType.INT
    
    def register_input(self, name: str, line: int):
        """Register an input variable that will be auto-declared."""
        self.inputs_pending.append((name, line))
    
    def get_input_variables(self) -> list:
        return self.inputs_pending
    
    def clear_inputs(self):
        self.inputs_pending.clear()


def infer_node_type(node, symtab: SymbolTable) -> VarType:
    """Infer type of an expression node."""
    from .ast_nodes import NodeType, BinaryOp, UnaryOp
    
    if node.node_type == NodeType.NUMBER:
        return VarType.INT
    elif node.node_type == NodeType.STRING:
        return VarType.STRING
    elif node.node_type == NodeType.IDENTIFIER:
        sym = symtab.lookup(node.name)
        return sym.type if sym else VarType.INT
    elif node.node_type == NodeType.BINARY_OP:
        # Arithmetic ops produce int, string concat produces string
        op = node.op
        if op == '+':
            left_type = infer_node_type(node.left, symtab)
            right_type = infer_node_type(node.right, symtab)
            if left_type == VarType.STRING or right_type == VarType.STRING:
                return VarType.STRING
        return VarType.INT
    elif node.node_type == NodeType.UNARY_OP:
        return VarType.INT
    
    return VarType.INT


def analyze_stmt(stmt, symtab: SymbolTable, errors: List) -> None:
    """Analyze a single statement in context."""
    from .ast_nodes import NodeType
    
    if stmt.node_type == NodeType.VAR_DECL:
        vartype = infer_node_type(stmt.value, symtab)
        err = symtab.declare(stmt.name, vartype, stmt.line)
        if err:
            errors.append((stmt.line, err, stmt.name))
    
    elif stmt.node_type == NodeType.ASSIGNMENT:
        err = symtab.ensure_declared(stmt.name, stmt.line)
        if err:
            errors.append((stmt.line, err, stmt.name))
    
    elif stmt.node_type == NodeType.INPUT:
        symtab.register_input(stmt.name, stmt.line)
    
    elif stmt.node_type == NodeType.IF:
        infer_node_type(stmt.condition, symtab)
        for s in stmt.then_branch:
            analyze_stmt(s, symtab, errors)
        for s in stmt.else_branch:
            analyze_stmt(s, symtab, errors)
    
    elif stmt.node_type == NodeType.WHILE:
        infer_node_type(stmt.condition, symtab)
        for s in stmt.body:
            analyze_stmt(s, symtab, errors)
    
    elif stmt.node_type == NodeType.FOR:
        infer_node_type(stmt.start, symtab)
        infer_node_type(stmt.end, symtab)
        for s in stmt.body:
            analyze_stmt(s, symtab, errors)


def analyze_types(ast) -> Tuple[SymbolTable, List]:
    """Analyze AST and build symbol table with type checking."""
    symtab = SymbolTable()
    errors: List = []
    for stmt in ast.statements:
        analyze_stmt(stmt, symtab, errors)
    return symtab, errors