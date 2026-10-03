"""Register the coding tools on one registry, rooted at one directory.

The handlers are the file, search, local-terminal, todo, clarify, web, and vision
tools. Web and vision do nothing on the network unless a transport is passed in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omes.tools.clarify import ClarifyLog, clarify
from omes.tools.file_ops import FileWorkspace
from omes.tools.registry import ToolRegistry
from omes.tools.search import search_text
from omes.tools.terminal import DEFAULT_TIMEOUT_SECONDS, run_terminal
from omes.tools.todo import TodoStore, todo_read, todo_write
from omes.tools.vision import vision_analyze
from omes.tools.web import web_extract, web_search

# Names offered to the model. omes/contracts/tool-rosters/omes.yaml lists these.
CODING_TOOL_NAMES = (
    "read_file",
    "write_file",
    "patch_file",
    "edit_file",
    "search_text",
    "run_terminal",
    "todo_write",
    "todo_read",
    "clarify",
    "web_search",
    "web_extract",
    "vision_analyze",
)


def register_coding_tools(
    registry: ToolRegistry,
    root: str | Path,
    web: Any = None,
    vision: Any = None,
) -> list[str]:
    """Register every coding tool. ``web`` and ``vision`` are injected transports."""
    workspace = FileWorkspace(root)
    store = TodoStore()
    log = ClarifyLog()
    root_path = workspace.root

    def read_file(path: str) -> dict:
        return workspace.read_file(path)

    def write_file(path: str, content: str) -> dict:
        return workspace.write_file(path, content)

    def patch_file(path: str, diff: str) -> dict:
        return workspace.patch_file(path, diff)

    def edit_file(path: str, diff: str) -> dict:
        return workspace.edit_file(path, diff)

    def search_text_tool(query: str, path: str = ".") -> dict:
        return search_text(root_path, query, path)

    def run_terminal_tool(
        argv: list[str],
        cwd: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict:
        return run_terminal(root_path, argv, cwd=cwd, timeout=timeout)

    def todo_write_tool(todos: list) -> dict:
        return todo_write(store, todos)

    def todo_read_tool() -> dict:
        return todo_read(store)

    def clarify_tool(question: str) -> dict:
        return clarify(log, question)

    def web_search_tool(query: str, limit: int = 5) -> Any:
        return web_search(web, query, limit=limit)

    def web_extract_tool(urls: list) -> Any:
        return web_extract(web, urls)

    def vision_analyze_tool(
        image_url: str,
        question: str,
        region: list | None = None,
    ) -> Any:
        return vision_analyze(vision, image_url, question, region=region)

    handlers = {
        "read_file": read_file,
        "write_file": write_file,
        "patch_file": patch_file,
        "edit_file": edit_file,
        "search_text": search_text_tool,
        "run_terminal": run_terminal_tool,
        "todo_write": todo_write_tool,
        "todo_read": todo_read_tool,
        "clarify": clarify_tool,
        "web_search": web_search_tool,
        "web_extract": web_extract_tool,
        "vision_analyze": vision_analyze_tool,
    }
    if set(handlers) != set(CODING_TOOL_NAMES):
        raise RuntimeError("coding tool handlers drifted from CODING_TOOL_NAMES")
    for name in CODING_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name])
    return list(CODING_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "read_file": (
        "Read a UTF-8 text file inside the workspace root. "
        "A path that escapes the root is an error. Returns the file contents.",
        _object(
            {"path": _string("File path, relative to the workspace root or absolute inside it.")},
            ["path"],
        ),
    ),
    "write_file": (
        "Write a UTF-8 text file inside the workspace root, replacing any existing content. "
        "Parent directories are created. A path that escapes the root is an error and writes nothing.",
        _object(
            {
                "path": _string("File path, relative to the workspace root or absolute inside it."),
                "content": _string("Full new contents of the file."),
            },
            ["path", "content"],
        ),
    ),
    "patch_file": (
        "Apply one unified diff to one file inside the workspace root. "
        "If a hunk's context does not match, the file is left byte-for-byte unchanged.",
        _object(
            {
                "path": _string("File the diff applies to."),
                "diff": _string("Unified diff (---/+++ headers and @@ hunks) for that one file."),
            },
            ["path", "diff"],
        ),
    ),
    "edit_file": (
        "Apply one unified diff to one file inside the workspace root, repairing "
        "hunks the exact apply cannot place by re-anchoring unique context or "
        "matching whitespace-insensitively. "
        "If no repair places every hunk, the file is left byte-for-byte unchanged.",
        _object(
            {
                "path": _string("File the diff applies to."),
                "diff": _string("Unified diff (---/+++ headers and @@ hunks) for that one file."),
            },
            ["path", "diff"],
        ),
    ),
    "search_text": (
        "Find a literal string under the workspace root and return the matching relative paths. "
        "The query is not a regular expression. Paths outside the root are not searched or returned.",
        _object(
            {
                "query": _string("Literal text to find. Not a regular expression."),
                "path": _string("Directory or file under the root to search. Defaults to the root."),
            },
            ["query"],
        ),
    ),
    "run_terminal": (
        "Run a program from an argv list with its working directory inside the workspace root. "
        "This is not a shell: the command string is not parsed or expanded. "
        "stdout, stderr, and the exit code are captured. A timeout stops the process. "
        "A working directory outside the root is refused.",
        _object(
            {
                "argv": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Program and arguments. Not a shell command string.",
                },
                "cwd": _string("Working directory inside the workspace root. Defaults to the root."),
                "timeout": {
                    "type": "number",
                    "description": "Seconds before the process is stopped.",
                    "default": DEFAULT_TIMEOUT_SECONDS,
                    "exclusiveMinimum": 0,
                },
            },
            ["argv"],
        ),
    ),
    "todo_write": (
        "Replace the in-memory task list with the given items. "
        "This is not a merge: items omitted from the list are dropped. Returns the stored list.",
        _object(
            {
                "todos": {
                    "type": "array",
                    "description": "The full task list. Each item is an object such as id, content, and status.",
                    "items": {"type": "object"},
                }
            },
            ["todos"],
        ),
    ),
    "todo_read": (
        "Return the task list last stored by todo_write.",
        _object({}, []),
    ),
    "clarify": (
        "Record a question for the user and return that same question.",
        _object(
            {"question": _string("The question to record and return.")},
            ["question"],
        ),
    ),
    "web_search": (
        "Search the web through the injected transport and return its payload. "
        "There is no default network client.",
        _object(
            {
                "query": _string("Search query passed to the transport."),
                "limit": {
                    "type": "integer",
                    "description": "Maximum results the transport should return.",
                    "default": 5,
                },
            },
            ["query"],
        ),
    ),
    "web_extract": (
        "Extract content for the given URLs through the injected transport and return its payload. "
        "There is no default network client.",
        _object(
            {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs the transport should extract.",
                }
            },
            ["urls"],
        ),
    ),
    "vision_analyze": (
        "Analyze an image through the injected transport and return its payload. "
        "There is no default network client.",
        _object(
            {
                "image_url": _string("Image URL, local path, or data URL passed to the transport."),
                "question": _string("Question about the image."),
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional [x1, y1, x2, y2] crop in image pixels.",
                },
            },
            ["image_url", "question"],
        ),
    ),
}


__all__ = ["CODING_TOOL_NAMES", "register_coding_tools"]
