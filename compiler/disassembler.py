class BytecodeDisassembler:
    def _format_arg(self, opcode, arg):
        if arg is None:
            return None
        if opcode == "DEFINE_FUNCTION":
            name = getattr(arg, "name", "?")
            params = getattr(arg, "params", [])
            defaults = getattr(arg, "defaults", {})
            vararg = getattr(arg, "vararg", None)
            kwarg = getattr(arg, "kwarg", None)
            parts = list(str(p) for p in params)
            if defaults:
                parts = [
                    f"{p}={defaults[p].__class__.__name__}" if p in defaults else p
                    for p in params
                ]
            if vararg:
                parts.append(f"*{vararg}")
            if kwarg:
                parts.append(f"**{kwarg}")
            return f"{name}({', '.join(parts)})"
        if opcode == "DEFINE_CLASS":
            name = getattr(arg, "name", "?")
            bases = getattr(arg, "bases", []) or []
            parent = getattr(arg, "parent", None)
            base_names = [str(b) for b in bases if b] or ([str(parent)] if parent else [])
            if base_names:
                return f"{name}({', '.join(base_names)})"
            return name
        if opcode == "MAKE_LAMBDA":
            params = getattr(arg, "params", [])
            return f"lambda {', '.join(str(p) for p in params)}"
        if opcode == "EXEC_WITH":
            return "<with-block>"
        return str(arg)

    def disassemble(self, instructions):
        lines = []
        for i, instr in enumerate(instructions):
            arg_str = self._format_arg(instr.opcode, instr.argument)
            if arg_str is None:
                lines.append(f"{i:04}  {instr.opcode}")
            else:
                lines.append(f"{i:04}  {instr.opcode} {arg_str}")
        return "\n".join(lines)