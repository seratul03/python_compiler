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
    """and / or"""
    def __init__(self, operator, left, right):
        self.operator = operator 
        self.left = left
        self.right = right


class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class AttributeAssignment(ASTNode):
    """obj.attr = value"""
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
    def __init__(self, name, params, body, decorators=None):
        self.name = name
        self.params = params
        self.body = body
        self.decorators = decorators or []


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
    """for var in iterable:"""
    def __init__(self, var_name, iterable, body):
        self.var_name = var_name
        self.iterable = iterable
        self.body = body


class RangeExpr(ASTNode):
    """range(start, stop[, step])"""
    def __init__(self, start, stop, step):
        self.start = start    
        self.stop = stop      
        self.step = step     


class ListComprehension(ASTNode):
    """[expr for var in iterable [if cond]]"""
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
    def __init__(self, name, parent, body):
        self.name = name
        self.parent = parent   
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
    """super().method(args) — calls parent-class method with self"""
    def __init__(self, method, args):
        self.method = method
        self.args = args


class MethodCallExpr(ASTNode):
    """method call on an arbitrary expression (not just a variable name)"""
    def __init__(self, obj_expr, method, args):
        self.obj_expr = obj_expr  
        self.method = method
        self.args = args           


class AttributeAccessExpr(ASTNode):
    """attribute access on an arbitrary expression"""
    def __init__(self, obj_expr, attr):
        self.obj_expr = obj_expr
        self.attr = attr


class ExprSubscript(ASTNode):
    """subscript on arbitrary expression: expr[index]  (e.g. self.items[i])"""
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
    """Wraps an expression used as a bare statement so its result is discarded (POP_TOP)."""
    def __init__(self, expr):
        self.expr = expr


class AugmentedAssignment(ASTNode):
    """name op= value  (e.g. x += 1)"""
    def __init__(self, name, operator, value):
        self.name = name        
        self.operator = operator
        self.value = value 


class AttributeAugAssignment(ASTNode):
    """obj.attr op= value  (e.g. self.count += 1)"""
    def __init__(self, obj, attr, operator, value):
        self.obj = obj
        self.attr = attr
        self.operator = operator
        self.value = value


class IndexAugAssignment(ASTNode):
    """name[index] op= value  (e.g. arr[i] += 1)"""
    def __init__(self, name, index, operator, value):
        self.name = name
        self.index = index
        self.operator = operator
        self.value = value
