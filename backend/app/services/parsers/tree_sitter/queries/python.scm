; ==========================================================
; Imports
; ==========================================================

(import_statement
  name: (dotted_name) @import.module
) @import.statement

(import_statement
  name: (aliased_import
    name: (dotted_name) @import.module
    alias: (identifier) @import.alias)
) @import.statement

(import_from_statement
  module_name: (dotted_name)? @import.from
  name: (dotted_name) @import.name
) @import.statement

(import_from_statement
  module_name: (dotted_name)? @import.from
  name: (aliased_import
    name: (dotted_name) @import.name
    alias: (identifier) @import.alias)
) @import.statement

; ==========================================================
; Classes
; ==========================================================

(class_definition
  name: (identifier) @class.name
) @class.definition

(class_definition
  superclasses: (argument_list
    (_) @class.base
  )
)
; ==========================================================
; Functions
; ==========================================================

(function_definition
  name: (identifier) @function.name
) @function.definition

(function_definition
  return_type: (_) @function.return_type
)
; ==========================================================
; Variables
; ==========================================================

(module
  (expression_statement
    (assignment
      left: (identifier) @variable.name
      right: (_) @variable.value
    ) @variable.definition
  )
)

(module
  (expression_statement
    (assignment
      left: (identifier) @variable.name
      type: (_) @variable.type
      right: (_) @variable.value
    ) @variable.definition
  )
)
; ==========================================================
; Documentation
; ==========================================================

(module
  .
  (expression_statement
    (string) @documentation.module
  )
)

(class_definition
  body: (block
    .
    (expression_statement
      (string) @documentation.class
    )
  )
)

(function_definition
  body: (block
    .
    (expression_statement
      (string) @documentation.function
    )
  )
)