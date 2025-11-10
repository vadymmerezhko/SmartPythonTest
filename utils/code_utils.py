import inspect
import os
import re
import sys
from typing import Optional


def get_caller_info(level=0):
    """
    Retrieve information about a specific caller from the current call stack.

    Args:
        level (int): The stack depth to inspect.
            - 0 → this function (get_caller_info itself)
            - 1 → the direct caller (e.g., your wrapper function)
            - 2 → the caller of the caller (e.g., the test code invoking the wrapper)
            Higher values walk further up the call stack.

    Returns:
        tuple[str, int, str]:
            - filename (str): Full absolute path of the source file.
            - lineno (int): Line number in the file where the call occurred.
            - code (str): The source code line at that position (empty string if unavailable).

    Example:
        >>> def demo():
        ...     return get_caller_info(level=1)
        >>> file, line, code = demo()
        >>> print(file, line, code)
        '/path/to/file.py', 42, 'return get_caller_info(level=1)'
    """
    stack = inspect.stack()
    caller_frame = stack[level]
    filename = caller_frame.filename
    lineno = caller_frame.lineno
    code = caller_frame.code_context[0].strip() if caller_frame.code_context else ""
    return filename, lineno, code


def get_function_parameters_index_map(call_expression: str) -> Optional[dict[int, str]]:
    """
    Parse a function call expression string and return a dictionary
    mapping parameter index to parameter name.
    All string literals are returned in single quotes like 'value'
    even when it was in double quotes in the function call: fill("value").

    Example:
        'login_page.login(username, password)'
        → {0: 'username', 1: 'password'}

    If parsing fails or the expression is not a function call, return None.
    """
    try:
        # Remove leading/trailing whitespace so AST can parse
        stripped_expr = call_expression.strip()

        tree = ast.parse(stripped_expr, mode="eval")  # parse expression
        if not isinstance(tree.body, ast.Call):
            return None

        mapping = {}
        for i, arg in enumerate(tree.body.args):
            if isinstance(arg, ast.Name):
                mapping[i] = arg.id  # variable name
            else:
                mapping[i] = ast.unparse(arg)  # literal, attr, etc.
        return mapping

    except Exception:
        return None


def update_value_in_function_call(line: str, param_index: int, old_value: str, new_value: str) -> str | None:
    """
    Replace a parameter by index in a function call expression,
    but only if its current value matches `old_value`.
    Preserves leading and trailing whitespace.
    """
    # Save leading and trailing whitespace
    leading = len(line) - len(line.lstrip(" "))
    suffix = line[len(line.rstrip(" ")):]  # preserves trailing spaces

    stripped_line = line.strip()
    if not stripped_line:
        return None

    # Parse into AST
    tree = ast.parse(stripped_line, mode="eval")
    if not isinstance(tree.body, ast.Call):
        raise ValueError("Line must be a function call expression")

    if param_index < 0 or param_index >= len(tree.body.args):
        raise IndexError(f"Parameter index {param_index} out of range")

    # Get current argument as AST node
    current_arg = tree.body.args[param_index]

    # Compare against old_value as AST node
    expected_ast = ast.parse(old_value, mode="eval").body
    if not ast.dump(current_arg) == ast.dump(expected_ast):
        return None

    # Replace with new_value AST node
    tree.body.args[param_index] = ast.parse(new_value, mode="eval").body
    updated_expr = ast.unparse(tree)

    return f"{' ' * leading}{updated_expr}{suffix}"


def replace_variable_assignment(line: str, var_name: str, new_value: str) -> Optional[str]:
    """
    Replace the RHS of a variable assignment in a line of code.
    Preserves the exact original indentation.
    Returns None if no match is found.

    Examples:
        replace_variable_assignment("username = 'admin'", "username", "'guest'")
        → "username = 'guest'"

        replace_variable_assignment("    username = \"admin\"", "username", "'guest'")
        → "    username = 'guest'"
    """
    # Capture leading whitespace
    m = re.match(r"^(\s*)", line)
    leading_ws = m.group(1) if m else ""

    # Match variable assignment (case-insensitive)
    pattern = re.compile(rf"^\s*({re.escape(var_name)})\s*=", re.IGNORECASE)
    if not pattern.match(line):
        return None

    # Extract left-hand side (strip only inside, keep indent separately)
    left, _, _ = line.partition("=")
    lhs = left.strip()

    # Build result with original indent
    return f"{leading_ws}{lhs} = {new_value}"


import ast

def get_parameter_index_from_function_def(filename: str, lineno: int, index: int) -> int:
    """
    Given a file and a line number, extract the argument name from a function call
    at that line and resolve it to the index in the enclosing function definition.

    Works for instance methods (self), class methods (cls), static methods, and plain functions.
    """
    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()
        lines = source.splitlines()

    # --- Step 1: Get the full call expression (handle multi-line)
    call_code = ""
    expr = None
    for i in range(lineno - 1, len(lines)):
        call_code += lines[i].strip() + "\n"
        try:
            expr = ast.parse(call_code, mode="eval").body
            if isinstance(expr, ast.Call):
                break
        except SyntaxError:
            continue
    if not isinstance(expr, ast.Call):
        return -1

    # --- Step 2: Extract argument name
    if index >= len(expr.args):
        return -1
    arg_node = expr.args[index]
    if not isinstance(arg_node, ast.Name):
        return -1
    arg_name = arg_node.id

    # --- Step 3: Parse the entire file
    tree = ast.parse(source)

    # --- Step 4: Find enclosing function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            if start <= lineno <= end:
                params = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
                if arg_name in params:
                    return params.index(arg_name)
    return -1


def get_data_provider_names_map(line: str) -> dict[str, int]:
    """
    Given a pytest parametrize header line, return a dict mapping parameter name -> index.

    Example:
        '@pytest.mark.parametrize("username,password,product", ['
        → {'username': 0, 'password': 1, 'product': 2}
    """
    # Regex to extract the quoted header list
    m = re.search(r'parametrize\(\s*["\']([^"\']+)["\']', line)
    if not m:
        return {}

    header = m.group(1)
    names = [name.strip() for name in header.split(",") if name.strip()]

    return {name: i for i, name in enumerate(names)}


def replace_variable_in_data_provider(row_line: str, column_index: int, new_value: str) -> str:
    """
    Replace a value at column_index in a pytest parametrize tuple row line.
    Preserves:
      - leading indentation
      - whether there was a trailing comma
    Returns the original line on any parsing error or invalid index.
    """
    try:
        # Capture leading indentation (spaces/tabs)
        m = re.match(r"^(\s*)", row_line)
        indent = m.group(1) if m else ""

        # Preserve whether there was a trailing comma
        has_comma = row_line.strip().endswith(",")

        # Trim for parsing, but keep indent for reconstruction
        stripped = row_line.strip().rstrip(",")  # remove trailing comma only for parsing

        tree = ast.parse(stripped, mode="eval")
        if not isinstance(tree.body, ast.Tuple):
            return None  # not a tuple expression

        elts = list(tree.body.elts)
        if not (0 <= column_index < len(elts)):
            return None  # out of bounds

        # Replace element
        tree.body.elts[column_index] = ast.parse(new_value, mode="eval").body

        updated_expr = ast.unparse(tree)

        # Rebuild with original indent and trailing comma (if present)
        return f"{indent}{updated_expr}{',' if has_comma else ''}"

    except Exception:
        return None


def normalize_args(fn, *args, **kwargs):
    """
    Ensure the first positional-or-keyword parameter is always in args[0].
    Leave keyword-only arguments in kwargs.
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    normalized_args = list(args)
    new_kwargs = dict(kwargs)

    for i, p in enumerate(params):
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            if len(normalized_args) <= i and p.name in new_kwargs:
                normalized_args.insert(i, new_kwargs.pop(p.name))
        # Stop after handling the first string input param
        if i == 0:
            break

    return tuple(normalized_args), new_kwargs


def get_parameter_index_from_stack(index: int = 0) -> int:
    """
    Return the parameter index (excluding 'self'/'cls') of the immediate caller's
    function, or -1 if the index is out of range or no suitable frame exists.
    """
    # stack[0] = this function, stack[1] = immediate caller
    stack = inspect.stack()
    if len(stack) < 2:
        return -1

    caller = stack[1]
    frame = caller.frame
    arg_info = inspect.getargvalues(frame)
    params = [a for a in arg_info.args if a not in ("self", "cls")]

    # no params or out-of-range → -1
    if index < 0 or index >= len(params):
        return -1

    # index is relative to params already (self/cls removed)
    return index


def get_effective_config_value(name: str, config: dict) -> str | None:
    """
    Returns the effective configuration value for a given name, following priority:
        1. Command-line parameter (--name=value)
        2. Config file value (case-insensitive)
        3. System environment variable (case-insensitive)

    Args:
        name (str): Variable name (case-insensitive, e.g. "BROWSER")
        config (dict): Configuration dictionary loaded from config.json

    Returns:
        str | None: Effective value or None if not found
    """
    name_lower = name.lower()

    # 1️ Command-line via raw sys.argv (--name=value)
    for arg in sys.argv:
        if arg.startswith("--") and "=" in arg:
            arg_name, arg_val = arg[2:].split("=", 1)
            if arg_name.lower() == name_lower:
                return arg_val.strip()

    # 2️ Config file
    for key, value in config.items():
        if key.lower() == name_lower:
            return str(value)

    # 3️ Environment variable
    for key, value in os.environ.items():
        if key.lower() == name_lower:
            return str(value)

    return None


def get_parameter_name_by_index(code: str, index: int) -> str | None:
    """
    Find a function parameter name by its positional index, using
    both the local file and imported modules.

    Example:
        get_parameter_name_by_index("login('user', 'pass')", 0)
        → "user"
    Supports class methods, static methods, free functions, and imported functions.
    """
    try:
        # --- 1. Parse function call safely ---
        tree = ast.parse(code.strip(), mode="eval")
        if not isinstance(tree.body, ast.Call):
            return None

        func = tree.body.func
        if isinstance(func, ast.Attribute):
            func_name = func.attr
        elif isinstance(func, ast.Name):
            func_name = func.id
        else:
            return None

        # --- 2. Locate the calling file ---
        frame_filename = None
        for frame_info in inspect.stack():
            filename = frame_info.filename
            if "/utils/" not in filename and "\\utils\\" not in filename:
                if os.path.exists(filename):
                    frame_filename = filename
                    break
        if not frame_filename:
            return None

        # --- 3. Try local file first ---
        try:
            with open(frame_filename, "r", encoding="utf-8") as f:
                module = ast.parse(f.read())
            for node in ast.walk(module):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    params = [a.arg for a in node.args.args]
                    if params and params[0] == "self":
                        params = params[1:]
                    if 0 <= index < len(params):
                        return params[index]
        except Exception:
            pass

        # --- 4. If not found, search in imported modules ---
        for mod_name, mod in list(sys.modules.items()):
            try:
                file_path = inspect.getsourcefile(mod)
                if not file_path or not os.path.exists(file_path):
                    continue
                with open(file_path, "r", encoding="utf-8") as f:
                    module = ast.parse(f.read())
                for node in ast.walk(module):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        params = [a.arg for a in node.args.args]
                        if params and params[0] == "self":
                            params = params[1:]
                        if 0 <= index < len(params):
                            return params[index]
            except Exception:
                continue

        return None
    except Exception:
        return None
