from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_python


def print_async(node, indent=0):
    if "async" in node.type or "function" in node.type:
        print("  " * indent + node.type)

    for child in node.children:
        print_async(child, indent + 1)


language = Language(tree_sitter_python.language())
parser = Parser(language)

source = Path(
    "tests/parsers/fixtures/python/sample.py"
).read_bytes()

tree = parser.parse(source)

print_async(tree.root_node)