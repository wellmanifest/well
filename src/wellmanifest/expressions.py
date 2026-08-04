from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import Any


class ExpressionError(ValueError):
    pass


class SafeExpressionEvaluator(ast.NodeVisitor):
    """A small, side-effect-free expression evaluator used by profiles and policies."""

    def __init__(self, context: Mapping[str, Any]):
        self.context = context

    def evaluate(self, expression: str) -> Any:
        normalized = expression.replace(" true", " True").replace(" false", " False").replace(" null", " None")
        if normalized.startswith("true"):
            normalized = "True" + normalized[4:]
        elif normalized.startswith("false"):
            normalized = "False" + normalized[5:]
        elif normalized.startswith("null"):
            normalized = "None" + normalized[4:]
        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError as exc:
            raise ExpressionError(f"Invalid expression: {expression}") from exc
        return self.visit(tree.body)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in {"True", "False", "None"}:
            return {"True": True, "False": False, "None": None}[node.id]
        if node.id not in self.context:
            raise ExpressionError(f"Unknown symbol: {node.id}")
        return self.context[node.id]

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        value = self.visit(node.value)
        if isinstance(value, Mapping):
            if node.attr not in value:
                raise ExpressionError(f"Unknown field: {node.attr}")
            return value[node.attr]
        if node.attr.startswith("_"):
            raise ExpressionError("Private attribute access is forbidden")
        try:
            return getattr(value, node.attr)
        except AttributeError as exc:
            raise ExpressionError(f"Unknown attribute: {node.attr}") from exc

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        value = self.visit(node.value)
        key = self.visit(node.slice)
        return value[key]

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(item) for item in node.elts)

    def visit_Dict(self, node: ast.Dict) -> dict[Any, Any]:
        return {self.visit(key): self.visit(value) for key, value in zip(node.keys, node.values, strict=True)}

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        if isinstance(node.op, ast.And):
            for value in node.values:
                if not self.visit(value):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for value in node.values:
                if self.visit(value):
                    return True
            return False
        raise ExpressionError("Unsupported boolean operator")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        value = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise ExpressionError("Unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise ExpressionError("Unsupported arithmetic operator")

    def visit_Compare(self, node: ast.Compare) -> bool:
        left = self.visit(node.left)
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            if isinstance(operator, ast.Eq):
                ok = left == right
            elif isinstance(operator, ast.NotEq):
                ok = left != right
            elif isinstance(operator, ast.Lt):
                ok = left < right
            elif isinstance(operator, ast.LtE):
                ok = left <= right
            elif isinstance(operator, ast.Gt):
                ok = left > right
            elif isinstance(operator, ast.GtE):
                ok = left >= right
            elif isinstance(operator, ast.In):
                ok = left in right
            elif isinstance(operator, ast.NotIn):
                ok = left not in right
            else:
                raise ExpressionError("Unsupported comparison operator")
            if not ok:
                return False
            left = right
        return True

    def generic_visit(self, node: ast.AST) -> Any:
        raise ExpressionError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_expression(expression: str, context: Mapping[str, Any]) -> Any:
    return SafeExpressionEvaluator(context).evaluate(expression)
