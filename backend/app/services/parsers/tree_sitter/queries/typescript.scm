; ==========================================================
; Imports
; ==========================================================

(import_statement) @import.statement

(import_statement
  source: (string) @import.module
)

(import_clause
  (identifier) @import.alias
)

(import_specifier
  name: (identifier) @import.name
)

(import_specifier
  alias: (identifier) @import.alias
)

(namespace_import
  (identifier) @import.alias
)

; ==========================================================
; Classes
; ==========================================================

(class_declaration) @class.definition

(class_declaration
  name: (type_identifier) @class.name
)

; Simplified - tree-sitter may not have class_heritage node in TS
; Will capture via other means if needed

; ==========================================================
; Interfaces
; ==========================================================

(interface_declaration) @interface.definition

(interface_declaration
  name: (type_identifier) @interface.name
)

; ==========================================================
; Type Aliases
; ==========================================================

(type_alias_declaration) @type.definition

(type_alias_declaration
  name: (type_identifier) @type.name
)

; ==========================================================
; Enums
; ==========================================================

(enum_declaration) @enum.definition

(enum_declaration
  name: (identifier) @enum.name
)

; ==========================================================
; Constructors
; ==========================================================

(method_definition
  name: (property_identifier) @constructor.name
  (#eq? @constructor.name "constructor")
) @constructor.definition

; ==========================================================
; Methods
; ==========================================================

(method_definition) @function.definition

(method_definition
  name: (property_identifier) @function.name
)

; ==========================================================
; Functions
; ==========================================================

(function_declaration) @function.definition

(function_declaration
  name: (identifier) @function.name
)

; ==========================================================
; Parameters
; ==========================================================

(required_parameter
  (identifier) @parameter.name
)

(optional_parameter
  (identifier) @parameter.name
)

(required_parameter
  type: (type_annotation) @parameter.type
)

(optional_parameter
  type: (type_annotation) @parameter.type
)

; ==========================================================
; Variables
; ==========================================================

(variable_declarator) @variable.definition

(variable_declarator
  name: (identifier) @variable.name
)

(variable_declarator
  value: (_) @variable.value
)

(variable_declarator
  type: (type_annotation) @variable.type
)

; ==========================================================
; Return Types
; ==========================================================

(function_declaration
  return_type: (type_annotation) @function.return_type
)

(method_definition
  return_type: (type_annotation) @function.return_type
)

; ==========================================================
; Decorators
; ==========================================================

(decorator) @decorator