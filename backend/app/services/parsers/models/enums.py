from enum import Enum


class SymbolType(str, Enum):
    IMPORT = "import"

    CLASS = "class"
    STRUCT = "struct"
    INTERFACE = "interface"
    ENUM = "enum"

    FUNCTION = "function"
    METHOD = "method"

    FIELD = "field"
    VARIABLE = "variable"
    PARAMETER = "parameter"

    MODULE = "module"
    PACKAGE = "package"

    CONSTRUCTOR = "constructor"


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"
    PACKAGE = "package"