; ==========================================================
; Package
; ==========================================================

(package_declaration
  (scoped_identifier) @namespace.name
)


; ==========================================================
; Imports
; ==========================================================

(import_declaration
  (scoped_identifier) @import.module
) @import.statement
; ==========================================================
; Classes
; ==========================================================

(class_declaration
  name: (identifier) @class.name
) @class.definition

(class_declaration
  superclass: (superclass
    (type_identifier) @class.base
  )
)

; ==========================================================
; Interfaces
; ==========================================================

(interface_declaration
  name: (identifier) @interface.name
) @interface.definition

; ==========================================================
; Fields
; ==========================================================

(field_declaration
  type: (_) @variable.type
  declarator: (variable_declarator
    name: (identifier) @variable.name
    value: (_) @variable.value
  )
) @variable.definition

; ==========================================================
; Enums
; ==========================================================

(enum_declaration
  name: (identifier) @enum.name
) @enum.definition

(enum_constant
  name: (identifier) @enum.value)
  
; ==========================================================
; Constructors
; ==========================================================

(constructor_declaration
  name: (identifier) @constructor.name
) @constructor.definition

; ==========================================================
; Methods
; ==========================================================

(method_declaration
  name: (identifier) @function.name
) @function.definition

(method_declaration
  type: (_) @function.return_type
)

; ==========================================================
; Parameters
; ==========================================================

(formal_parameter
  type: (_) @parameter.type
  name: (identifier) @parameter.name
)

; ==========================================================
; Annotations
; ==========================================================

(marker_annotation
  name: (identifier) @annotation.name
)

; ==========================================================
; Implemented Interfaces
; ==========================================================

(class_declaration
  interfaces: (super_interfaces
    (type_list
      (type_identifier) @class.interface
    )
  )
)