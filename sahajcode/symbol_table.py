"""
SahajCode Symbol Table
Tracks variable names, types, and scope during parsing and code generation.
"""

from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from .ast_nodes import NodeType


class VarType(Enum):
    INT = 'int'
    STRING = 'string'


class Symbol:
    """Represents a variable symbol."""
    def __init__(self, name: str, var_type: VarType, line_declared: int, is_initialized: bool = False,
                 is_array: bool = False, size: int = 0):
        self.name = name
        self.type = var_type
        self.line_declared = line_declared
        self.is_initialized = is_initialized
        self.is_array = is_array
        self.size = size
    
    def __repr__(self):
        return f"Symbol({self.name}: {self.type.value})"


@dataclass
class FunctionInfo:
    """Represents a user-defined function."""
    name: str
    params: List[str] = field(default_factory=list)
    return_type: VarType = VarType.INT
    body: List = field(default_factory=list)


class SymbolTable:
    """Global scope symbol table for SahajCode MVP."""
    
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.inputs_pending: List[Tuple[str, int]] = []  # Variables from suna that need declaration
        self.functions: Dict[str, FunctionInfo] = {}
    
    def declare(self, name: str, var_type: VarType, line: int, is_array: bool = False, size: int = 0) -> Optional[str]:
        """Declare a variable. Returns error message if redeclaration."""
        if name in self.symbols:
            return f"'{name}' पहिले नै परिभाषित भएको छ"
        self.symbols[name] = Symbol(name, var_type, line, is_initialized=True, is_array=is_array, size=size)
        return None
    
    def declare_function(self, info: FunctionInfo) -> Optional[str]:
        if info.name in self.functions:
            return f"'{info.name}' नामको फंक्शन पहिले नै छ"
        self.functions[info.name] = info
        return None
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a variable."""
        return self.symbols.get(name)
    
    def lookup_function(self, name: str) -> Optional[FunctionInfo]:
        return self.functions.get(name)
    
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


def analyze_stmt(stmt, symtab: SymbolTable, errors: List, in_function: bool = False) -> None:
    """Analyze a single statement in context."""
    from .ast_nodes import NodeType
    
    if stmt.node_type == NodeType.VAR_DECL:
        is_array = stmt.value is not None and stmt.value.node_type == NodeType.ARRAY_LITERAL
        if is_array:
            # element type from the first literal element
            first = stmt.value.elements[0] if stmt.value.elements else None
            elem = infer_node_type(first, symtab) if first is not None else VarType.INT
            stmt.value.elem_type = 'string' if elem == VarType.STRING else 'int'
            vartype = elem
            size = stmt.value.size
        else:
            vartype = infer_node_type(stmt.value, symtab)
            size = 0
        if not in_function:
            err = symtab.declare(stmt.name, vartype, stmt.line, is_array=is_array, size=size)
            if err:
                errors.append((stmt.line, err, stmt.name))
        # inside a function, locals are declared at code-gen time
    
    elif stmt.node_type == NodeType.ASSIGNMENT:
        # target may be a bare identifier or an array index
        if hasattr(stmt, 'target') and isinstance(stmt.target, object) and getattr(stmt.target, 'node_type', None) == NodeType.INDEX:
            target = stmt.target.array
        else:
            target = stmt.name
        if not in_function:
            err = symtab.ensure_declared(target, stmt.line)
            if err:
                errors.append((stmt.line, err, target))
    
    elif stmt.node_type == NodeType.INPUT:
        if not in_function:
            symtab.register_input(stmt.name, stmt.line)
    
    elif stmt.node_type == NodeType.FUNCTION_DEF:
        # register signature; analyze body in its own scope
        info = FunctionInfo(name=stmt.name, params=list(stmt.params), body=stmt.body)
        err = symtab.declare_function(info)
        if err:
            errors.append((stmt.line, err, stmt.name))
        # analyze body statements in function context
        for s in stmt.body:
            analyze_stmt(s, symtab, errors, in_function=True)
    
    elif stmt.node_type == NodeType.IF:
        infer_node_type(stmt.condition, symtab)
        for s in stmt.then_branch:
            analyze_stmt(s, symtab, errors, in_function)
        for s in stmt.else_branch:
            analyze_stmt(s, symtab, errors, in_function)
    
    elif stmt.node_type == NodeType.WHILE:
        infer_node_type(stmt.condition, symtab)
        for s in stmt.body:
            analyze_stmt(s, symtab, errors, in_function)
    
    elif stmt.node_type == NodeType.FOR:
        infer_node_type(stmt.start, symtab)
        infer_node_type(stmt.end, symtab)
        for s in stmt.body:
            analyze_stmt(s, symtab, errors, in_function)


def analyze_types(ast) -> Tuple[SymbolTable, List]:
    """Analyze AST and build symbol table with type checking."""
    symtab = SymbolTable()
    errors: List = []
    for stmt in ast.statements:
        analyze_stmt(stmt, symtab, errors)
    return symtab, errors