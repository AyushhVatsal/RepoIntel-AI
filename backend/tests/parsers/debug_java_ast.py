from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_java


def print_tree(node, indent: int = 0) -> None:
    """
    Recursively print the Tree-sitter AST.
    """

    print("  " * indent + node.type)

    for child in node.named_children:
        print_tree(child, indent + 1)


def main() -> None:

    language = Language(tree_sitter_java.language())
    parser = Parser(language)

    source = Path(
        "tests/parsers/fixtures/java/Animal.java"
    ).read_bytes()

    tree = parser.parse(source)

    print(tree.root_node)


if __name__ == "__main__":
    main()