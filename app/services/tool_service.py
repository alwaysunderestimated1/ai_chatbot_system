import ast
import math
import operator
from datetime import datetime, timezone
from typing import Any

from app.services import rag_service

# --- Safe math evaluator ---
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil,
    "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn:
            return fn(*[_eval_node(a) for a in node.args])
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def _safe_calc(expression: str) -> str:
    try:
        result = _eval_node(ast.parse(expression.strip(), mode="eval").body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# --- OpenAI tool definitions ---
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Returns the current UTC date and time in ISO 8601 format.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Safely evaluate a mathematical expression. "
                "Supports +, -, *, /, **, %, //, sqrt, abs, round, floor, ceil, "
                "log, log10, sin, cos, tan, pi, e."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. 'sqrt(16) + 2 * pi'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the internal knowledge base for information relevant to a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (1–10, default 3)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "get_current_datetime":
        return datetime.now(timezone.utc).isoformat()

    if name == "calculate":
        return _safe_calc(arguments.get("expression", ""))

    if name == "search_knowledge_base":
        query = arguments.get("query", "")
        top_k = min(int(arguments.get("top_k", 3)), 10)
        results = await rag_service.retrieve(query, top_k=top_k)
        if not results:
            return "No relevant information found in the knowledge base."
        return "\n\n".join(
            f"[{r.filename}, chunk {r.chunk_index}] (score: {r.score:.3f})\n{r.content}"
            for r in results
        )

    return f"Unknown tool: {name}"
