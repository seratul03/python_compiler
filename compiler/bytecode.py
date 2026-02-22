class Instruction:
    def __init__(self, opcode, argument=None):
        self.opcode = opcode
        self.argument = argument


class BytecodeGenerator:
    def __init__(self):
        self.instructions = []

    def generate(self, node):
        method = getattr(self, f"visit_{type(node).__name__}")
        return method(node)

    def visit_Program(self, node):
        for stmt in node.statements:
            self.generate(stmt)
        return self.instructions

    def visit_Number(self, node):
        self.instructions.append(Instruction("LOAD_CONST", node.value))

    def visit_Variable(self, node):
        self.instructions.append(Instruction("LOAD_VAR", node.name))

    def visit_Assignment(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("STORE_VAR", node.name))

    def visit_Print(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("PRINT"))

    def visit_BinaryOp(self, node):
        self.generate(node.left)
        self.generate(node.right)

        op_map = {
            "+": "ADD",
            "-": "SUB",
            "*": "MUL",
            "/": "DIV"
        }

        self.instructions.append(Instruction(op_map[node.operator]))

    def visit_Compare(self, node):
        self.generate(node.left)
        self.generate(node.right)
        self.instructions.append(Instruction("COMPARE", node.operator))

    def visit_IfStatement(self, node):
        self.generate(node.condition)

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        for stmt in node.body:
            self.generate(stmt)

        jump_end = len(self.instructions)
        self.instructions.append(Instruction("JUMP", None))

        self.instructions[jump_false].argument = len(self.instructions)

        for stmt in node.else_body:
            self.generate(stmt)

        self.instructions[jump_end].argument = len(self.instructions)

    def visit_WhileLoop(self, node):
        loop_start = len(self.instructions)

        self.generate(node.condition)

        jump_false = len(self.instructions)
        self.instructions.append(Instruction("JUMP_IF_FALSE", None))

        for stmt in node.body:
            self.generate(stmt)

        self.instructions.append(Instruction("JUMP", loop_start))

        self.instructions[jump_false].argument = len(self.instructions)

    def visit_FunctionDef(self, node):
        self.instructions.append(Instruction("DEFINE_FUNCTION", node))

    def visit_FunctionCall(self, node):
        for arg in node.args:
            self.generate(arg)

        self.instructions.append(
            Instruction("CALL_FUNCTION", (node.name, len(node.args)))
        )

    def visit_Return(self, node):
        self.generate(node.value)
        self.instructions.append(Instruction("RETURN_VALUE"))
    
    def visit_ListLiteral(self, node):
        for element in node.elements:
            self.generate(element)
        self.instructions.append(
            Instruction("BUILD_LIST", len(node.elements))
        )


def visit_ListAccess(self, node):
    self.instructions.append(Instruction("LOAD_VAR", node.name))
    self.generate(node.index)
    self.instructions.append(Instruction("LOAD_INDEX"))


def visit_IndexAssignment(self, node):
    self.instructions.append(Instruction("LOAD_VAR", node.name))
    self.generate(node.index)
    self.generate(node.value)
    self.instructions.append(Instruction("STORE_INDEX"))


def visit_ForLoop(self, node):
    # initialize counter
    self.generate(node.start)
    self.instructions.append(Instruction("STORE_VAR", node.var_name))

    loop_start = len(self.instructions)

    self.instructions.append(Instruction("LOAD_VAR", node.var_name))
    self.generate(node.end)
    self.instructions.append(Instruction("COMPARE", "<"))

    jump_false = len(self.instructions)
    self.instructions.append(Instruction("JUMP_IF_FALSE", None))

    for stmt in node.body:
        self.generate(stmt)

    self.instructions.append(Instruction("LOAD_VAR", node.var_name))
    self.instructions.append(Instruction("LOAD_CONST", 1))
    self.instructions.append(Instruction("ADD"))
    self.instructions.append(Instruction("STORE_VAR", node.var_name))

    self.instructions.append(Instruction("JUMP", loop_start))
    self.instructions[jump_false].argument = len(self.instructions)