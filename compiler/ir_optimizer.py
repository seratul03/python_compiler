from compiler.ir import IRInstruction


class IROptimizer:
    """Simple IR-level optimizer used by the compiler execution pipeline."""

    _BINARY_OPS = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b,
        "%": lambda a, b: a % b,
        "**": lambda a, b: a ** b,
        "//": lambda a, b: a // b,
    }

    _COMPARE_OPS = {
        "<": lambda a, b: a < b,
        ">": lambda a, b: a > b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<=": lambda a, b: a <= b,
        ">=": lambda a, b: a >= b,
        "is": lambda a, b: a is b,
        "is not": lambda a, b: a is not b,
        "in": lambda a, b: a in b,
        "not in": lambda a, b: a not in b,
    }

    def _fold_binary(self, op, left, right):
        try:
            if op in self._BINARY_OPS:
                return True, self._BINARY_OPS[op](left, right)
            if op in self._COMPARE_OPS:
                return True, self._COMPARE_OPS[op](left, right)
            if op == "BOOL_AND":
                return True, bool(left and right)
            if op == "BOOL_OR":
                return True, bool(left or right)
        except Exception:
            return False, None
        return False, None

    def _fold_unary(self, op, value):
        try:
            if op == "UNARY_NEG":
                return True, -value
            if op == "UNARY_NOT":
                return True, not value
        except Exception:
            return False, None
        return False, None

    def optimize(self, instructions):
        constants = {}
        optimized = []

        for instr in instructions:
            op = instr.op

            if op == "CONST":
                constants[instr.result] = instr.arg1
                optimized.append(instr)
                continue

            if op in self._BINARY_OPS or op in self._COMPARE_OPS or op in ("BOOL_AND", "BOOL_OR"):
                if isinstance(instr.arg1, str) and isinstance(instr.arg2, str):
                    if instr.arg1 in constants and instr.arg2 in constants:
                        ok, folded = self._fold_binary(op, constants[instr.arg1], constants[instr.arg2])
                        if ok:
                            constants[instr.result] = folded
                            optimized.append(IRInstruction("CONST", folded, None, instr.result))
                            continue

            if op in ("UNARY_NEG", "UNARY_NOT") and isinstance(instr.arg1, str):
                if instr.arg1 in constants:
                    ok, folded = self._fold_unary(op, constants[instr.arg1])
                    if ok:
                        constants[instr.result] = folded
                        optimized.append(IRInstruction("CONST", folded, None, instr.result))
                        continue

            if op == "ASSIGN" and isinstance(instr.arg1, str) and instr.arg1 in constants:
                constants[instr.result] = constants[instr.arg1]
            elif instr.result is not None:
                constants.pop(instr.result, None)

            optimized.append(instr)

        return optimized
