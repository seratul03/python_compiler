class IRInstruction:
    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def __repr__(self):
        if self.op == "LABEL":
            return f"{self.arg1}:"
        elif self.op in ("JUMP", "JUMP_IF_FALSE"):
            return f"{self.op} {self.arg1}"
        elif self.result:
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        elif self.arg1:
            return f"{self.op} {self.arg1}"
        return f"{self.op}"

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
        value = self.generate(node.value)
        self.instructions.append(
            IRInstruction("PRINT", value)
        )
    def visit_Compare(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)

        temp = self.new_temp()
        self.instructions.append(
            IRInstruction("COMPARE", left, right, temp)
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

        for stmt in node.else_body:
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