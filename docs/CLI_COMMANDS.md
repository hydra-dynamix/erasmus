# Erasmus CLI Command Reference

This document provides a comprehensive reference for all Erasmus CLI commands, arguments, and usage patterns.

---

## Top-Level Commands

- `erasmus context` — Manage development contexts and their files
- `erasmus protocol` — Manage development protocols
- `erasmus setup` — Setup Erasmus: initialize project, environment, and context
- `erasmus watch` — Watch for `.ctx` file changes and update the IDE rules file automatically
- `erasmus status` — Show the current Erasmus context and protocol status
- `erasmus version` — Show the Erasmus version

---

## Context Commands

### List all contexts

```bash
erasmus context list
```

### Create a new context

```bash
erasmus context create [NAME]
```

- Prompts for a name if not provided.

### Show context details

```bash
erasmus context show [NAME]
```

- Prompts for a context if not provided.

### Update context files

```bash
erasmus context update [NAME] [FILE_TYPE] [CONTENT]
```

- `FILE_TYPE` can be: `architecture`, `progress`, `tasks`, `protocol`

### Edit context files

```bash
erasmus context edit [NAME] [FILE_TYPE] [EDITOR]
```

### Store the current context

```bash
erasmus context store
```

### Select and load a context interactively

```bash
erasmus context select
```

### Load a context by name to root .ctx XML files

```bash
erasmus context load [NAME]
```

### Delete a context

```bash
erasmus context delete [NAME]
```

- Prompts for a context if not provided.

---

## Protocol Commands

### List all protocols

```bash
erasmus protocol list
```

### Create a new protocol

```bash
erasmus protocol create [NAME] [CONTENT]
```

- Prompts for name/content if not provided.

### Show protocol details

```bash
erasmus protocol show [NAME]
```

- Prompts for a protocol if not provided.

### Update a protocol

```bash
erasmus protocol update [NAME] [CONTENT]
```

### Edit a protocol

```bash
erasmus protocol edit [NAME] [EDITOR]
```

### Delete a protocol

```bash
erasmus protocol delete [NAME]
```

- Prompts for a protocol if not provided.

### Select and display a protocol

```bash
erasmus protocol select
```

### Load a protocol as active

```bash
erasmus protocol load [NAME]
```

---

## Setup Command

### Interactive setup for Erasmus

```bash
erasmus setup
```

- Guides you through IDE detection, project creation, context and protocol setup.

---

## Other Top-Level Commands

### Watch for .ctx file changes

```bash
erasmus watch
```

- Watches for changes and updates IDE rules files automatically.

### Show current status

```bash
erasmus status
```

- Displays current context, available contexts, and protocols.

### Show Erasmus version

```bash
erasmus version
```

---

## Help

For more information about a command, run:

```bash
erasmus <command> --help
```
