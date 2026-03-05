class BytecodeDisassembler:
    def disassemble(self, instructions):
        lines = []

        for i, instr in enumerate(instructions):
            if instr.argument is None:
                lines.append(f"{i:04}  {instr.opcode}")
            else:
                lines.append(f"{i:04}  {instr.opcode} {instr.argument}")

        return "\n".join(lines)