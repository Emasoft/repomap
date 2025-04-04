;; Functions
(function_definition
  name: (identifier) @name.definition.function)

;; Methods
(class_definition
  body: (block
          (function_definition
            name: (identifier) @name.definition.method)))

;; Classes
(class_definition
  name: (identifier) @name.definition.class)

;; Variable definitions
(assignment 
  left: (identifier) @name.definition.variable)

;; Imports
(import_statement
  name: (dotted_name) @name.definition.import)

;; Parameters
(parameters
  (identifier) @name.reference.parameter)

;; References
(call
  function: (identifier) @name.reference.call)

(call
  function: (attribute
              attribute: (identifier) @name.reference.call))

(identifier) @name.reference