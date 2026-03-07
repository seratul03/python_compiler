class ASTNode:
    pass


class Number(ASTNode):
    def __init__(self, value):
        self.value = value


class Float(ASTNode):
    def __init__(self, value):
        self.value = value


class String(ASTNode):
    def __init__(self, value):
        self.value = value


class BoolLiteral(ASTNode):
    def __init__(self, value):
        self.value = value


class NoneLiteral(ASTNode):
    pass


class Variable(ASTNode):
    def __init__(self, name):
        self.name = name


class BinaryOp(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class UnaryOp(ASTNode):
    def __init__(self, operator, operand):
        self.operator = operator 
        self.operand = operand


class BoolOp(ASTNode):
    def __init__(self, operator, left, right):
        self.operator = operator 
        self.left = left
        self.right = right


class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class AttributeAssignment(ASTNode):
    def __init__(self, obj, attr, value):
        self.obj = obj     
        self.attr = attr   
        self.value = value


class Print(ASTNode):
    def __init__(self, values):
        self.values = values


class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class IfStatement(ASTNode):
    def __init__(self, condition, body, else_body):
        self.condition = condition
        self.body = body
        self.else_body = else_body


class Compare(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class WhileLoop(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body


class FunctionDef(ASTNode):
    def __init__(self, name, params, body, decorators=None,
                 defaults=None, vararg=None, kwarg=None, kwonly_params=None, annotations=None):
        self.name = name
        self.params = params          # list of positional param names (str)
        self.body = body
        self.decorators = decorators or []
        self.defaults = defaults or {}  # {param_name: default_node}
        self.vararg = vararg            # name of *args param (str or None)
        self.kwarg = kwarg              # name of **kwargs param (str or None)
        self.kwonly_params = kwonly_params or []  # params after *args
        self.annotations = annotations or {}      # type hints (ignored at runtime)


class Return(ASTNode):
    def __init__(self, value):
        self.value = value


class FunctionCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args


class ListLiteral(ASTNode):
    def __init__(self, elements):
        self.elements = elements


class ListAccess(ASTNode):
    def __init__(self, name, index):
        self.name = name
        self.index = index

class ForLoop(ASTNode):
    def __init__(self, var_name, start, end, body):
        self.var_name = var_name
        self.start = start
        self.end = end
        self.body = body


class ForInLoop(ASTNode):
    def __init__(self, var_name, iterable, body):
        self.var_name = var_name
        self.iterable = iterable
        self.body = body


class RangeExpr(ASTNode):
    def __init__(self, start, stop, step):
        self.start = start    
        self.stop = stop      
        self.step = step     


class ListComprehension(ASTNode):
    def __init__(self, expr, var_name, iterable, condition=None):
        self.expr = expr
        self.var_name = var_name
        self.iterable = iterable
        self.condition = condition


class IndexAssignment(ASTNode):
    def __init__(self, name, index, value):
        self.name = name
        self.index = index
        self.value = value


class ClassDef(ASTNode):
    def __init__(self, name, parent, body, bases=None):
        self.name = name
        self.parent = parent        # first base (kept for backward compat)
        self.bases = bases or ([parent] if parent else [])  # all bases
        self.body = body


class AttributeAccess(ASTNode):
    def __init__(self, obj, attr):
        self.obj = obj    
        self.attr = attr  


class MethodCall(ASTNode):
    def __init__(self, obj, method, args):
        self.obj = obj       
        self.method = method 
        self.args = args


class SuperMethodCall(ASTNode):
    def __init__(self, method, args, explicit_class=None):
        self.method = method
        self.args = args
        self.explicit_class = explicit_class


class MethodCallExpr(ASTNode):
    def __init__(self, obj_expr, method, args):
        self.obj_expr = obj_expr  
        self.method = method
        self.args = args           


class AttributeAccessExpr(ASTNode):
    def __init__(self, obj_expr, attr):
        self.obj_expr = obj_expr
        self.attr = attr


class ExprSubscript(ASTNode):
    def __init__(self, obj_expr, index):
        self.obj_expr = obj_expr
        self.index = index


class Break(ASTNode):
    pass


class Continue(ASTNode):
    pass


class Pass(ASTNode):
    pass


class ExprStatement(ASTNode):
    def __init__(self, expr):
        self.expr = expr


class AugmentedAssignment(ASTNode):
    def __init__(self, name, operator, value):
        self.name = name        
        self.operator = operator
        self.value = value 


class AttributeAugAssignment(ASTNode):
    def __init__(self, obj, attr, operator, value):
        self.obj = obj
        self.attr = attr
        self.operator = operator
        self.value = value


class IndexAugAssignment(ASTNode):
    def __init__(self, name, index, operator, value):
        self.name = name
        self.index = index
        self.operator = operator
        self.value = value


class TupleLiteral(ASTNode):
    def __init__(self, elements):
        self.elements = elements


class UnpackAssignment(ASTNode):
    def __init__(self, names, value):
        self.names = names  
        self.value = value


class ChainedIndexAssignment(ASTNode):
    def __init__(self, name, indices, value):
        self.name = name       
        self.indices = indices 
        self.value = value


class FStringExpr(ASTNode):
    def __init__(self, parts):
        self.parts = parts


class Import(ASTNode):
    """import mod1 [as a1], mod2 [as a2], ..."""
    def __init__(self, names):        
        self.names = names


class ImportFrom(ASTNode):
    """from module import name1 [as a1], ..."""
    def __init__(self, module, names):
        self.module = module
        self.names = names


class ExceptHandler(ASTNode):
    def __init__(self, exc_type, var_name, body):
        self.exc_type = exc_type  
        self.var_name = var_name    
        self.body = body


class TryExcept(ASTNode):
    def __init__(self, body, handlers, else_body=None, finally_body=None):
        self.body = body
        self.handlers = handlers        
        self.else_body = else_body or []
        self.finally_body = finally_body or []


class WithStatement(ASTNode):
    def __init__(self, items, body):
        self.items = items
        self.body = body


class RaiseStatement(ASTNode):
    def __init__(self, exc=None, cause=None):
        self.exc = exc
        self.cause = cause


class DeleteStatement(ASTNode):
    def __init__(self, targets):
        self.targets = targets      


class GlobalStatement(ASTNode):
    def __init__(self, names):
        self.names = names


class NonlocalStatement(ASTNode):
    def __init__(self, names):
        self.names = names


class YieldExpr(ASTNode):
    def __init__(self, value=None):
        self.value = value


class LambdaExpr(ASTNode):
    def __init__(self, params, body, defaults=None, vararg=None, kwarg=None):
        self.params = params            
        self.body = body                
        self.defaults = defaults or {}
        self.vararg = vararg
        self.kwarg = kwarg


class Assert(ASTNode):
    def __init__(self, condition, message=None):
        self.condition = condition
        self.message = message


class DictLiteral(ASTNode):
    """{ k1: v1, k2: v2, **spread, ... }"""
    def __init__(self, keys, values):
        self.keys = keys        
        self.values = values


class SetLiteral(ASTNode):
    def __init__(self, elements):
        self.elements = elements


class DictComprehension(ASTNode):
    def __init__(self, key_expr, val_expr, var_name, iterable, condition=None):
        self.key_expr = key_expr
        self.val_expr = val_expr
        self.var_name = var_name
        self.iterable = iterable
        self.condition = condition


class SetComprehension(ASTNode):
    def __init__(self, expr, var_name, iterable, condition=None):
        self.expr = expr
        self.var_name = var_name
        self.iterable = iterable
        self.condition = condition


class GeneratorExpr(ASTNode):
    def __init__(self, expr, var_name, iterable, condition=None):
        self.expr = expr
        self.var_name = var_name
        self.iterable = iterable
        self.condition = condition


class Slice(ASTNode):
    def __init__(self, start, stop, step=None):
        self.start = start
        self.stop = stop
        self.step = step


class Starred(ASTNode):
    """*expr — used in calls and assignments"""
    def __init__(self, value):
        self.value = value


class DoubleStarred(ASTNode):
    """**expr — used in calls and dict literals"""
    def __init__(self, value):
        self.value = value


class KeywordArg(ASTNode):
    """name=value inside a function call"""
    def __init__(self, name, value):
        self.name = name
        self.value = value


class WalrusExpr(ASTNode):
    """:= named expression"""
    def __init__(self, name, value):
        self.name = name
        self.value = value


class IfExpr(ASTNode):
    """Ternary: body if condition else orelse"""
    def __init__(self, condition, body, orelse):
        self.condition = condition
        self.body = body
        self.orelse = orelse


class EllipsisNode(ASTNode):
    pass


class Decorated(ASTNode):
    """@decorator\\n def/class ..."""
    def __init__(self, decorators, node):
        self.decorators = decorators    
        self.node = node                


class BitwiseOp(ASTNode):
    """Bitwise binary operations: &  |  ^  <<  >>"""
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class UnaryBitNot(ASTNode):
    """~operand"""
    def __init__(self, operand):
        self.operand = operand
