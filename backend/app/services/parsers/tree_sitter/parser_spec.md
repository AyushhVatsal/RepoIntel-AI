# RepoIntel Parser Specification

Version: 2.0

Status: Stable

---

# 1. Purpose

This document defines the semantic parser contract used throughout RepoIntel.

Every Tier 1 language MUST map its Tree-sitter grammar to this specification.

The parser pipeline must never depend directly on language-specific grammar nodes.

Instead, every language adapter emits the semantic captures defined in this document.

This allows Python, Java, JavaScript, TypeScript, and future languages to produce the same intermediate representation.

Pipeline:

Source Code
    ↓
Tree-sitter Grammar
    ↓
Language Query (.scm)
    ↓
Semantic Captures (This Specification)
    ↓
SymbolExtractor
    ↓
ParsedDocument
    ↓
Architecture / Chunking / Embeddings / RAG

---

# 2. Design Principles

Every Tier 1 language must satisfy these principles.

## Language Agnostic

The parser never asks

- Is this Python?
- Is this Java?

Instead it asks

- Is this a Type?
- Is this a Function?
- Is this an Import?

---

## Stable Capture Names

Capture names are part of the public parser contract.

They must remain stable across languages.

Example

Python

class User

↓

@type.definition

Java

class User

↓

@type.definition

TypeScript

class User

↓

@type.definition

---

## Semantic First

Languages may have different grammar.

RepoIntel only cares about semantic meaning.

Examples

Python Decorator

↓

Annotation

Java Annotation

↓

Annotation

C# Attribute

↓

Annotation

---

## Extensible

Adding a new Tier 1 language must require only

- LanguageConfig
- Tree-sitter grammar
- .scm query

The rest of the parser should remain unchanged.

---

# 3. Semantic Objects

RepoIntel understands the following semantic objects.

1. Namespace
2. Import
3. Type
4. Constructor
5. Function
6. Parameter
7. Variable
8. Annotation
9. Documentation

These are the only concepts downstream modules should depend on.

---

# 4. Namespace

Represents language-level namespaces.

Examples

Java

package com.example.auth;

C#

namespace Authentication

Python

Module

Capture Names

@namespace.definition

@namespace.name

Required

No

---

# 5. Imports

Represents dependency declarations.

Examples

Python

import os

from pathlib import Path

Java

import java.util.List;

JavaScript

import React from "react";

Capture Names

@import.statement

@import.module

@import.name

@import.alias

@import.static

Required

@import.statement

@import.module

Optional

@import.alias

@import.name

@import.static

---

# 6. Types

Represents every user-defined type.

Includes

Class

Interface

Enum

Record

Struct

Future language-specific types

Examples

Python

class User

Java

class User

interface UserRepository

enum Status

TypeScript

class User

interface User

enum Status

Capture Names

@type.definition

@type.name

@type.base

@type.interface

@type.modifier

@type.kind

Required

@type.definition

@type.name

Optional

@type.base

@type.interface

@type.modifier

@type.kind

---

# 7. Constructors

Represents constructors.

Examples

Java

User()

TypeScript

constructor()

Capture Names

@constructor.definition

@constructor.name

Required

No

---

# 8. Functions

Represents executable routines.

Includes

Functions

Methods

Async functions

Generator functions

Capture Names

@function.definition

@function.name

@function.return_type

@function.modifier

@function.async

@function.generator

Required

@function.definition

@function.name

Optional

Everything else

---

# 9. Parameters

Represents function parameters.

Capture Names

@parameter.name

@parameter.type

@parameter.default

@parameter.variadic

@parameter.keyword_only

Required

@parameter.name

Optional

Everything else

---

# 10. Variables

Represents top-level variables and fields.

Does NOT include local variables.

Capture Names

@variable.definition

@variable.name

@variable.type

@variable.value

@variable.modifier

Required

None

---

# 11. Annotations

Represents metadata attached to declarations.

Maps

Python

Decorator

↓

Annotation

Java

Annotation

↓

Annotation

C#

Attribute

↓

Annotation

Capture Names

@annotation.definition

@annotation.name

Required

No

---

# 12. Documentation

Represents documentation attached to declarations.

Maps

Python

Docstring

Java

JavaDoc

JavaScript

JSDoc

TypeScript

TSDoc

Capture Names

@documentation.module

@documentation.type

@documentation.function

@documentation.variable

Required

No

---

# 13. Tier Requirements

## Tier 1

Must provide

✓ AST

✓ Tree-sitter grammar

✓ Semantic captures

✓ Symbol extraction

✓ Architecture support

✓ Dependency analysis

Supported Languages

Python

Java

JavaScript

TypeScript

---

## Tier 0

Provides

✓ File loading

✓ Text chunking

✓ Embedding

✓ Semantic search

No AST.

No symbol extraction.

No architecture analysis.

Examples

Go

Rust

PHP

Ruby

HTML

CSS

SCSS

Swift

Kotlin

Lua

Shell

R

MATLAB

---

# 14. Language Mapping

| Semantic Object | Python | Java | JavaScript | TypeScript |
|-----------------|---------|------|------------|------------|
| Namespace | Module | Package | Module | Module |
| Import | import | import | import | import |
| Type | class | class/interface/enum | class | class/interface/enum |
| Constructor | __init__ | constructor | constructor | constructor |
| Function | function | method | function | function |
| Annotation | decorator | annotation | decorator | decorator |
| Documentation | docstring | JavaDoc | JSDoc | TSDoc |

---

# 15. Naming Rules

Every Tier 1 query MUST emit the semantic capture names defined in this document.

Do NOT invent language-specific capture names.

Good

@type.definition

Bad

@class.definition

Good

@annotation.name

Bad

@decorator.name

Good

@documentation.function

Bad

@docstring.function

---

# 16. Future Extensions

The following semantic objects may be added in future parser versions.

Call

Reference

Inheritance

Generic

Lambda

Exception

Module

Macro

Trait

Record Component

Pattern

Expression

Statement

These are intentionally excluded from Version 2.

---

# 17. Compatibility

Adding a new Tier 1 language must require only

1. Register the language.

2. Add Tree-sitter grammar.

3. Implement the .scm query using this specification.

4. Extend SymbolExtractor only where the grammar introduces new node structures.

No downstream module should require modification.

---

# 18. Summary

RepoIntel is built around semantic concepts rather than language syntax.

Every language adapts its grammar to this specification.

The parser architecture remains stable as new languages are added, allowing the rest of the platform to operate on a single, language-independent intermediate representation.