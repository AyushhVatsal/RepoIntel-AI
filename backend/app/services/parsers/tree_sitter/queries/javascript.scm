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
  name: (identifier) @class.name
)

(class_heritage
  (identifier) @class.base
)

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

(formal_parameters
  (identifier) @parameter.name
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