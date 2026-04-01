class IRInstruction:
    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def __repr__(self):
        if self.op == "LABEL":
            return f"{self.arg1}:"
        if self.op == "JUMP":
            return f"JUMP {self.arg1}"
        if self.op == "JUMP_IF_FALSE":
            return f"JUMP_IF_FALSE {self.arg2} {self.arg1}"
        if self.op == "CONST":
            return f"{self.result} = {self.arg1!r}"
        if self.op == "ASSIGN":
            return f"{self.result} = {self.arg1}"
        if self.op == "PRINT":
            return f"PRINT {self.arg1}"
        if self.op == "RETURN":
            return f"RETURN {self.arg1}"
        if self.op == "CALL":
            args = self.arg2 if isinstance(self.arg2, list) else []
            return f"{self.result} = CALL {self.arg1}({', '.join(map(str, args))})"
        if self.op == "LIST":
            elems = self.arg1 if isinstance(self.arg1, list) else []
            return f"{self.result} = LIST [{', '.join(map(str, elems))}]"
        if self.op == "INDEX":
            return f"{self.result} = {self.arg1}[{self.arg2}]"
        if self.result is not None:
            if self.arg2 is None:
                return f"{self.result} = {self.op} {self.arg1}"
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        if self.arg1 is not None:
            return f"{self.op} {self.arg1}"
        return self.op

class IRGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def generate(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method:
            return method(node)

    def visit_Program(self, node):
        for stmt in node.statements:
            self.generate(stmt)
        return self.instructions

    def visit_Assignment(self, node):
        value = self.generate(node.value)
        self.instructions.append(
            IRInstruction("ASSIGN", value, None, node.name)
        )

    def visit_Number(self, node):
        temp = self.new_temp()
        self.instructions.append(
            IRInstruction("CONST", node.value, None, temp)
        )
        return temp

    def visit_Float(self, node):
        temp = self.new_temp()
        self.instructions.append(
            IRInstruction("CONST", node.value, None, temp)
        )
        return temp

    def visit_BoolLiteral(self, node):
        temp = self.new_temp()
        self.instructions.append(
            IRInstruction("CONST", node.value, None, temp)
        )
        return temp

    def visit_NoneLiteral(self, node):
        temp = self.new_temp()
        self.instructions.append(
            IRInstruction("CONST", None, None, temp)
        )
        return temp

    def visit_Variable(self, node):
        return node.name

    def visit_BinaryOp(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)

        temp = self.new_temp()
        self.instructions.append(
            IRInstruction(node.operator, left, right, temp)
        )
        return temp

    def visit_Print(self, node):
        values = getattr(node, "values", None)
        if values is None:
            values = [getattr(node, "value", None)]
        for value_node in values:
            value = self.generate(value_node)
            self.instructions.append(
                IRInstruction("PRINT", value)
            )

    def visit_ExprStatement(self, node):
        return self.generate(node.expr)

    def visit_Compare(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)

        temp = self.new_temp()
        self.instructions.append(
            IRInstruction(node.operator, left, right, temp)
        )
        return temp
    
    def visit_IfStatement(self, node):
        condition = self.generate(node.condition)

        else_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(
            IRInstruction("JUMP_IF_FALSE", else_label, condition)
        )

        for stmt in node.body:
            self.generate(stmt)

        self.instructions.append(
            IRInstruction("JUMP", end_label)
        )

        self.instructions.append(
            IRInstruction("LABEL", else_label)
        )

        for stmt in (node.else_body or []):
            self.generate(stmt)

        self.instructions.append(
            IRInstruction("LABEL", end_label)
        )
    
    def visit_WhileLoop(self, node):
        start_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(
            IRInstruction("LABEL", start_label)
        )

        condition = self.generate(node.condition)

        self.instructions.append(
            IRInstruction("JUMP_IF_FALSE", end_label, condition)
        )

        for stmt in node.body:
            self.generate(stmt)

        self.instructions.append(
            IRInstruction("JUMP", start_label)
        )

        self.instructions.append(
            IRInstruction("LABEL", end_label)
        )

    def visit_FunctionDef(self, node):
        self.instructions.append(
            IRInstruction("DEFINE_FUNCTION", node.name, node, None)
        )

    def visit_Return(self, node):
        value = self.generate(node.value)
        self.instructions.append(
            IRInstruction("RETURN", value)
        )

    def visit_FunctionCall(self, node):
        args = []

        for arg in node.args:
            args.append(self.generate(arg))

        temp = self.new_temp()

        self.instructions.append(
            IRInstruction("CALL", node.name, args, temp)
        )

        return temp

    def visit_ListLiteral(self, node):
        elements = [self.generate(e) for e in node.elements]

        temp = self.new_temp()

        self.instructions.append(
            IRInstruction("LIST", elements, None, temp)
        )

        return temp

    def visit_ListAccess(self, node):
        index = self.generate(node.index)

        temp = self.new_temp()

        self.instructions.append(
            IRInstruction("INDEX", node.name, index, temp)
        )

        return temp
    
    def visit_String(self, node):
        temp = self.new_temp()

        self.instructions.append(
        IRInstruction("CONST", node.value, None, temp)
    )

        return temp


    def visit_ForLoop(self, node):

        start = self.generate(node.start)
        end = self.generate(node.end)

        loop_var = node.var_name

        start_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(
            IRInstruction("ASSIGN", start, None, loop_var)
        )

        self.instructions.append(
            IRInstruction("LABEL", start_label)
        )

        cond_temp = self.new_temp()

        self.instructions.append(
            IRInstruction("<", loop_var, end, cond_temp)
        )

        self.instructions.append(
            IRInstruction("JUMP_IF_FALSE", end_label, cond_temp)
        )

        for stmt in node.body:
            self.generate(stmt)

        one_temp = self.new_temp()
        self.instructions.append(
            IRInstruction("CONST", 1, None, one_temp)
        )

        inc_temp = self.new_temp()
        self.instructions.append(
            IRInstruction("+", loop_var, one_temp, inc_temp)
        )

        self.instructions.append(
            IRInstruction("ASSIGN", inc_temp, None, loop_var)
        )

        self.instructions.append(
            IRInstruction("JUMP", start_label)
        )

        self.instructions.append(
            IRInstruction("LABEL", end_label)
        )