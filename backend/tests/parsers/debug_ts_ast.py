from pathlib import Path

from tree_sitter import Parser, Language
from tree_sitter_typescript import language_typescript


def walk(node, source, depth=0):
    indent = "    " * depth
    text = source[node.start_byte:node.end_byte].decode("utf-8")

    print(
        f"{indent}{node.type}"
        f" [{node.start_point} -> {node.end_point}]"
        f" : {text!r}"
    )

    for child in node.named_children:
        walk(
            child,
            source,
            depth + 1,
        )


def main():

    source = Path(
        "tests/parsers/fixtures/ts/sample.ts"
    ).read_bytes()

    parser = Parser(
        Language(
            language_typescript()
        )
    )

    tree = parser.parse(source)

    walk(
        tree.root_node,
        source,
    )


if __name__ == "__main__":
    main()