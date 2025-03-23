# Type Checking with mypy

This project uses [mypy](https://mypy.readthedocs.io/) for static type checking. We have configured mypy to enforce strict typing for the `src/orcs` directory.

## Setup

1. **Installation**: mypy is already included in the development dependencies. If you need to install it manually, run:
   ```bash
   pip install mypy
   ```

2. **Configuration**: mypy is configured in `pyproject.toml` with strict typing rules for the `src/orcs` directory.

3. **Pre-commit Hook**: A pre-commit hook is set up to run mypy checks before each commit for files in `src/orcs`.

## Type Checking Tools

We've created several helper scripts to assist with the typing process:

1. **add_type_annotations.py**: Shows current typing issues and provides guidance.
   ```bash
   python add_type_annotations.py
   ```

2. **add_explicit_optional.py**: Automatically fixes implicit Optional issues.
   ```bash
   python add_explicit_optional.py
   ```

3. **typing_progress.py**: Analyzes and prioritizes files for fixing type issues.
   ```bash
   python typing_progress.py
   ```

## Running Type Checks

You can run type checks manually:

```bash
# Check the entire orcs directory
mypy src/orcs

# Check a specific file
mypy src/orcs/path/to/file.py

# Show more context for errors
mypy --show-error-context src/orcs
```

## Guidelines for Adding Type Annotations

1. **Start with Return Types**: Add return types to functions first, as these are often simpler than parameter types.
   ```python
   def my_function() -> None:
       pass
   ```

2. **Use Optional for Nullable Values**: Always use `Optional[Type]` for values that can be `None`.
   ```python
   from typing import Optional
   
   def process_data(data: Optional[str] = None) -> str:
       if data is None:
           return "default"
       return data
   ```

3. **Be Specific with Collections**: Use specific types for collections.
   ```python
   from typing import List, Dict
   
   def get_names() -> List[str]:
       return ["alice", "bob"]
       
   def get_ages() -> Dict[str, int]:
       return {"alice": 30, "bob": 25}
   ```

4. **Type Ignores**: Use `# type: ignore` comments for issues you can't fix immediately, but add a comment explaining why.
   ```python
   imported_value = complex_import()  # type: ignore  # External library without type hints
   ```

5. **Type Annotations for Variables**: Add type annotations for complex variables.
   ```python
   from typing import Dict, List
   
   # Add type annotation for complex data structures
   user_data: Dict[str, List[str]] = {}
   ```

## Gradual Typing Approach

We're adopting a gradual approach to adding type annotations:

1. Start with smaller, simpler files (use `typing_progress.py` to prioritize)
2. Add type annotations to new code as it's written
3. When modifying existing code, add type annotations to functions you touch
4. Use the pre-commit hook to ensure type correctness before committing

## Common Issues and Solutions

- **Import Errors**: For third-party libraries without type stubs, consider installing type stubs or using `# type: ignore`.
- **Any Type**: Avoid using `Any` unless absolutely necessary; it defeats the purpose of static typing.
- **Union Types**: Use `Union[Type1, Type2]` for values that can be of multiple types.
- **Missing Return Types**: Always add return type annotations, even if the function returns `None`.
- **Generic Types**: Always specify type parameters for generic types like `List`, `Dict`, etc.

## Resources

- [mypy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Typing Module Documentation](https://docs.python.org/3/library/typing.html) 