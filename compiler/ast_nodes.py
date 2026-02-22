class Number:
    def __init__(self, value):
        self.value = value


class Variable:
    def __init__(self, name):
        self.name = name


class BinaryOp:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class Assignment:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Print:
    def __init__(self, value):
        self.value = value


class Program:
    def __init__(self, statements):
        self.statements = statements


class IfStatement:
    def __init__(self, condition, body, else_body):
        self.condition = condition
        self.body = body
        self.else_body = else_body


class Compare:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

class WhileLoop:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class FunctionDef:
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body


class Return:
    def __init__(self, value):
        self.value = value


class FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class ListLiteral:
    def __init__(self, elements):
        self.elements = elements


class ListAccess:
    def __init__(self, name, index):
        self.name = name
        self.index = index

class ForLoop:
    def __init__(self, var_name, start, end, body):
        self.var_name = var_name
        self.start = start
        self.end = end
        self.body = body


class IndexAssignment:
    def __init__(self, name, index, value):
        self.name = name
        self.index = index
        self.value = value


class ClassDef:
    def __init__(self, name, body):
        self.name = name
        self.body = body


class AttributeAccess:
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr


class MethodCall:
    def __init__(self, obj, method, args):
        self.obj = obj
        self.method = method
        self.args = args