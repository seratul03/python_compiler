class SymbolTable:
                                                                             

    def __init__(self):
        self.symbols = {}

    def define(self, name, value_type):
        self.symbols[name] = value_type

    def lookup(self, name):
        return self.symbols.get(name)

    def exists(self, name):
        return name in self.symbols

    def all_symbols(self):
        return dict(self.symbols)