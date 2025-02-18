from antlr4 import *
from edbs.EDBSParser import EDBSParser
from edbs.EDBSLexer import EDBSLexer
from edbs.EDBSVisitor import EDBSVisitor


class ExitCall(Exception):
    pass

class Module:

    def __init__(self, formal_params, result, body):
        self.formal_params = formal_params
        self.result = result
        self.body = body


class SymbolTable:

    def __init__(self):
        self.storage = {}
        self.modules = {}

    def add_var(self, name: str, value: float):
        self.storage[name] = value

    def get_var(self, name: str):
        if name not in self.storage:
            raise KeyError(f"Variable {name} not found!!")
        return self.storage[name]

    def is_defined(self, name: str):
        return name in self.storage


class CollectActualParams(EDBSVisitor):

    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.values = []

    def visitActual_param_list(self, ctx:EDBSParser.Actual_param_listContext):
        for p in ctx.getChildren():
            self.visit(p)


    def visitActual_param(self, ctx:EDBSParser.Actual_paramContext):
        if ctx.IDENTIFIER() is not None:
            self.values.append(self.symbol_table.get_var(str(ctx.IDENTIFIER())))
        elif ctx.NUMBER():
            self.values.append(float(str(ctx.NUMBER()).replace(".","").replace(",",".")))
        else:
            self.values.append(self.visit(ctx.str_literal()))

    def visitStr_literal(self, ctx:EDBSParser.Str_literalContext):
        if ctx.STRING() is not None:
            return str(ctx.STRING())[1:-1]
        elif ctx.NEWLINE_CHAR():
            return '\n'
        elif ctx.WHITESPACE_CHAR():
            return ' '
        elif ctx.NULL_CHAR():
            return None


class InterpreterVisitor(EDBSVisitor):

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table


    def visitModule_def(self, ctx:EDBSParser.Module_defContext):
        name = str(ctx.IDENTIFIER())
        params = self.visit(ctx.input_params())
        result = self.visit(ctx.output_params())
        ctx.output_params()
        m = Module(params, result, ctx.module_body())
        self.symbol_table.modules[name] = m

    def visitOutput_params(self, ctx:EDBSParser.Output_paramsContext):
        return str(ctx.IDENTIFIER())

    def visitInput_params(self, ctx:EDBSParser.Input_paramsContext):
        return self.visit(ctx.param_list())

    def visitParam_list(self, ctx:EDBSParser.Param_listContext):
        idx = 0
        current = ctx.IDENTIFIER(idx)
        result = []
        while current is not None:
            result.append(str(current))
            idx += 1
            current = ctx.IDENTIFIER(idx)
        return result

    def visitWrite_arg(self, ctx:EDBSParser.Write_argContext):
        if ctx.IDENTIFIER() is not None:
            name = str(ctx.IDENTIFIER())
            value = self.symbol_table.get_var(name)
            if isinstance(value, float):
                value = str(round(value, 2)).replace(".", ",")
            print(str(value), end=" ")
        elif ctx.STRING():
            string_token = ctx.STRING()
            print(str(string_token)[1:-1], end=" ")

    def visitWrite(self, ctx:EDBSParser.WriteContext):
        for c in ctx.children:
            self.visit(c)
        print()

    def visitRead(self, ctx:EDBSParser.ReadContext):
        prompt = str(ctx.STRING())[1:-1]
        value = float(input(f"{prompt}: ").replace(".", "").replace(",", "."))
        name = str(ctx.IDENTIFIER())
        self.symbol_table.add_var(name, value)

    def visitCalc(self, ctx:EDBSParser.CalcContext):
        name = str(ctx.IDENTIFIER())
        value = self.visit(ctx.expression())
        # if self.symbol_table.is_defined(name):
        #     raise KeyError(f"Stedfortreter med namn «{name}» finnast allerede!")
        self.symbol_table.add_var(name, value)

    def visitMutate(self, ctx:EDBSParser.MutateContext):
        name = str(ctx.IDENTIFIER())
        if not self.symbol_table.is_defined(name):
            self.symbol_table.add_var(name,0.0)
        value = self.visit(ctx.expression())
        self.symbol_table.add_var(name, value)

    def visitWhile(self, ctx:EDBSParser.WhileContext):
        is_satisfied =  self.visit(ctx.bool_expr())
        while is_satisfied:
            for c in ctx.children:
                self.visit(c)
            is_satisfied = self.visit(ctx.bool_expr())

    def visitStrlit(self, ctx:EDBSParser.StrlitContext):
        return self.visit(ctx.str_literal())

    def visitStr_literal(self, ctx:EDBSParser.Str_literalContext):
        if ctx.STRING() is not None:
            return str(ctx.STRING())[1:-1]
        elif ctx.NEWLINE_CHAR():
            return '\n'
        elif ctx.WHITESPACE_CHAR():
            return ' '
        elif ctx.NULL_CHAR():
            return None

    def visitNolit(self, ctx:EDBSParser.NolitContext):
        value = float(str(ctx.NUMBER()).replace(",", '.'))
        return value

    def visitVar(self, ctx:EDBSParser.VarContext):
        name = str(ctx.IDENTIFIER())
        value = self.symbol_table.get_var(name)
        return value

    def visitAdd(self, ctx:EDBSParser.AddContext):
        return self.visit(ctx.getChild(0)) + self.visit(ctx.getChild(2))

    def visitDiv(self, ctx:EDBSParser.DivContext):
        return self.visit(ctx.getChild(0)) / self.visit(ctx.getChild(2))

    def visitMul(self, ctx:EDBSParser.MulContext):
        return self.visit(ctx.getChild(0)) * self.visit(ctx.getChild(2))

    def visitSub(self, ctx:EDBSParser.SubContext):
        return self.visit(ctx.getChild(0)) - self.visit(ctx.getChild(2))

    def visitExpo(self, ctx:EDBSParser.ExpoContext):
        return self.visit(ctx.getChild(0)) ** self.visit(ctx.getChild(2))

    def visitNested(self, ctx:EDBSParser.NestedContext):
        return self.visit(ctx.expression())

    def visitListop(self, ctx:EDBSParser.ListopContext):
        return None # TODO: hugseliste

    def visitCall(self, ctx:EDBSParser.CallContext):
        name = str(ctx.IDENTIFIER())
        collect_actuals = CollectActualParams(self.symbol_table)
        collect_actuals.visit(ctx.actual_param_list())
        module = self.symbol_table.modules[name]
        for p, v in zip(module.formal_params, collect_actuals.values):
            self.symbol_table.add_var(p, v)
        try:
            self.visit(module.body)
        except ExitCall:
            pass # TODO: error handling
        return self.symbol_table.get_var(module.result)

    # bool expressions

    def visitComp(self, ctx:EDBSParser.CompContext):
        return self.visit(ctx.comparison())

    def visitComparison(self, ctx:EDBSParser.ComparisonContext):
        lhs = self.visit(ctx.getChild(0))
        rhs = self.visit(ctx.getChild(ctx.getChildCount() - 1))
        if ctx.COMP_EQL() is not None:
            return lhs == rhs
        elif ctx.COMP_LT() is not None:
            return lhs < rhs
        elif ctx.COMP_LEQ() is not None:
            return lhs <= rhs
        elif ctx.COMP_GT() is not None:
            return lhs > rhs
        elif ctx.COMP_GEQ() is not None:
            return lhs >= rhs

    def visitAnd(self, ctx:EDBSParser.AndContext):
        return self.visit(ctx.getChild(0)) and self.visit(ctx.getChild(2))

    def visitOr(self, ctx:EDBSParser.OrContext):
        return self.visit(ctx.getChild(0)) or self.visitComp(ctx.getChild(2))

    def visitNot(self, ctx:EDBSParser.NotContext):
        return not self.visit(ctx.bool_expr())


def main():

    input_stream = FileStream("../examples/modules.edbs", encoding="utf-8")
    lexer = EDBSLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = EDBSParser(token_stream)
    tree = parser.program()
    table = SymbolTable()
    visitor = InterpreterVisitor(table)
    visitor.visit(tree)

if __name__ == '__main__':
    main()
