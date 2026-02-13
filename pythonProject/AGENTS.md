# AGENTS.md - Coding Guidelines for AI Agents

This file provides guidelines for AI agents working on this Python LangChain-based AI agent project.

## Build, Lint, and Test Commands

### Environment Setup
```bash
# Activate virtual environment (Windows)
pythonProject/.venv/Scripts/activate

# Or use the venv Python directly
pythonProject/.venv/Scripts/python -m <module>
```

### Running Tests
```bash
# Run all tests
python -m pytest

# Run a single test file
python -m pytest path/to/test_file.py

# Run a single test function
python -m pytest path/to/test_file.py::test_function_name

# Run a single test class
python -m pytest path/to/test_file.py::TestClassName

# Run with verbose output
python -m pytest -v

# Run with coverage report
python -m pytest --cov=. --cov-report=term-missing
```

### Linting and Formatting
```bash
# Format code with black
python -m black .

# Check code style with flake8
python -m flake8 .

# Type checking with mypy
python -m mypy .

# Run all checks
python -m black --check . && python -m flake8 . && python -m mypy .
```

### Running the Application
```bash
# Run agent modules
python -m ai.agent.agent_core.graph_core

# Run LangChain examples
python langchain/agents.py
```

## Code Style Guidelines

### Indentation and Formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use double quotes for strings, except for single-character strings or to avoid escaping
- Add trailing commas in multi-line lists, dicts, and function arguments

### Naming Conventions
- **Variables**: `snake_case` (e.g., `user_preferences`, `tool_call_list`)
- **Functions**: `snake_case` with descriptive verbs (e.g., `get_user_preference`, `detect_file_encoding`)
- **Classes**: `PascalCase` (e.g., `AgentState`, `UserIntent`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BINARY_FILE_EXTENSIONS`, `DEFAULT_MAX_FILE_SIZE`)
- **Type variables**: `PascalCase` with descriptive names (e.g., `AgentState`, `ToolCallRequest`)
- **Private functions/vars**: prefix with underscore (e.g., `_is_binary_file`)

### Import Organization
Order imports in three groups with blank lines between:
1. Standard library imports
2. Third-party imports (langchain, pydantic, etc.)
3. Local application imports

```python
# Standard library
import os
import stat
import shutil
from pathlib import Path
from typing import Literal, TypedDict, Any

# Third-party
from langchain_core.tools import tool
from langchain.graph import StateGraph
from pydantic import BaseModel, Field

# Local imports
from ai.agent.ai_config.config import gen_llm_qwq_235b
from ai.cad_agent_release.agent_core.prompt import *
```

### Type Hints
- Use type hints for all function parameters and return types
- Use `| None` for optional types (Python 3.10+ style, not `Optional[...]`)
- Use `Literal[...]` for string enums
- Use `TypedDict` for dictionary structures
- Use `BaseModel` from pydantic for complex data structures

```python
from typing import TypedDict, Literal, Any
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    agent_input: str | None
    agent_type: Literal['cad_run', 'cad_rag', 'general_chat'] | None

def process_data(
    input_data: str,
    options: dict[str, Any] | None = None
) -> dict[str, Any]:
    ...
```

### Error Handling
- Use try/except blocks for operations that may fail
- Catch specific exceptions, avoid bare `except:`
- Provide meaningful error messages
- Use custom error messages for tool failures

```python
try:
    mime = magic.from_file(file_path, mime=True)
    return not mime.startswith('text/')
except Exception:
    with open(file_path, 'rb') as f:
        chunk = f.read(1024)
    return b'\x00' in chunk
```

### Docstrings and Comments
- Use triple-double quotes for docstrings
- Document function purpose, args, and return values
- Keep comments concise and relevant
- Write comments in English for consistency

```python
def smart_truncate(
        content: str,
        max_length: int,
        file_ext: str = None
) -> tuple[str, bool]:
    """
    Truncate a string to a specified length, preserving semantic integrity.
    """
```

### Function Definitions
- Use type hints for all parameters
- Use default values appropriately
- Keep functions focused on a single responsibility
- Use descriptive parameter names

```python
@tool
def code_gen_opt(
        code_lang: Literal['python', 'tcl', 'verilog'],
        task: Literal['generate', 'optimize'],
        task_desc: str,
        existing_code: str | None = None,
):
    """Generate or optimize code in specified languages."""
```

### Working with LangChain
- Use the `@tool` decorator for tool functions
- Use `TypedDict` for agent state definitions
- Use pydantic `BaseModel` for structured outputs
- Leverage middleware patterns for cross-cutting concerns

```python
from langchain_core.tools import tool
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    context: dict | None

@tool
def my_tool(input_param: str) -> str:
    """Tool description."""
    return f"Processed: {input_param}"
```

### Constants and Configuration
- Define constants at module level
- Use UPPER_SNAKE_CASE for constants
- Group related constants together

```python
BINARY_FILE_EXTENSIONS = {
    ".exe", ".dll", '.so', '.bin', '.zip',
    '.tar', '.gz', '.bz2', '.7z', '.rar',
}

DEFAULT_MAX_FILE_SIZE = 200 * 1024
```

## Project Structure

```
pythonProject/
├── ai/
│   ├── agent/
│   │   ├── agent_core/      # Core agent logic
│   │   ├── ai_config/       # Configuration
│   │   ├── rag/            # RAG components
│   │   └── tools/          # Tool definitions
│   ├── RACG/               # RACG module
│   └── spec2rtl/           # Spec to RTL conversion
├── langchain/              # LangChain examples and experiments
└── .venv/                  # Virtual environment
```

## Best Practices

1. **Always read existing files** before making changes
2. **Ask when uncertain** - don't guess about requirements
3. **Make minimal changes** - only modify what's necessary
4. **Test your changes** - run relevant tests before submitting
5. **Follow existing patterns** - match the style of surrounding code
6. **Handle errors gracefully** - provide meaningful error messages
7. **Use type hints consistently** - they improve code clarity
8. **Keep functions small and focused** - single responsibility principle

## Dependencies

Key dependencies used in this project:
- `langchain` / `langchain-core` - LLM framework
- `langgraph` - Graph-based agent orchestration
- `pydantic` - Data validation and settings
- `python-magic` - File type detection
- `chardet` - Character encoding detection

Always check if a library is already in use before adding new dependencies.
