class ASTNode:
    def accept(self, visitor):
        method_name = "visit_" + self.__class__.__name__
        visit = getattr(visitor, method_name, visitor.generic_visit)
        return visit(self)

    def __repr__(self):
        attrs = ", ".join(
            f"{k}={v}" for k, v in self.__dict__.items()
        )
        return f"{self.__class__.__name__}({attrs})"

class Number(ASTNode):
    def __init__(self, value):
        self.value = value

class Variable(ASTNode):
    def __init__(self, name):
        self.name = name

class BinaryOp(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

class Compare(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class IndexAssignment(ASTNode):
    def __init__(self, name, index, value):
        self.name = name
        self.index = index
        self.value = value

class Print(ASTNode):
    def __init__(self, value):
        self.value = value

class Return(ASTNode):
    def __init__(self, value):
        self.value = value

class IfStatement(ASTNode):
    def __init__(self, condition, body, else_body):
        self.condition = condition
        self.body = body
        self.else_body = else_body

class WhileLoop(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForLoop(ASTNode):
    def __init__(self, var_name, start, end, body):
        self.var_name = var_name
        self.start = start
        self.end = end
        self.body = body

class FunctionDef(ASTNode):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body


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

class ClassDef(ASTNode):
    def __init__(self, name, body):
        self.name = name
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