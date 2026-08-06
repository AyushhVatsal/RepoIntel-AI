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
; Parameters
; ==========================================================

(parameters
  (identifier) @parameter.name
)

(parameters
  (typed_parameter
    (identifier) @parameter.name
  )
)

(parameters
  (typed_default_parameter
    name: (identifier) @parameter.name
  )
)


; ==========================================================
; Decorators
; ==========================================================

(decorator
  (identifier) @decorator.name
)

(decorator
  (attribute) @decorator.name
)


; ==========================================================
; Module Variables
; ==========================================================

(module
  (expression_statement
    (assignment
      left: (identifier) @variable.name
    ) @variable.definition
  )
)


; ==========================================================
; Module Docstring
; ==========================================================

(module
  .
  (expression_statement
    (string) @docstring.module
  )
)


; ==========================================================
; Class Docstring
; ==========================================================

(class_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.class
    )
  )
)


; ==========================================================
; Function Docstring
; ==========================================================

(function_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.function
    )
  )
)