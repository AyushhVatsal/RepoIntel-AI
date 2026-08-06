from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_python

language = Language(tree_sitter_python.language())
parser = Parser(language)

source = Path(
    "tests/parsers/fixtures/python/sample.py"
).read_bytes()

tree = parser.parse(source)

print(tree.root_node)