"""Minimal Gemini REST client for `generateContent` (text, optional file attachments, structured JSON)."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

MODEL_LIST = [
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-2.5-computer-use-preview-10-2025",
    "gemini-3.1-pro-preview",
    "gemini-3.1-pro-preview-customtools",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]

# Default schema for `generate_content_structured`: one or more files + optional notes.
MULTIFILE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "description": (
                "Generated files to write under a project root. "
                "Use forward slashes in relative_path. Order is arbitrary. "
                "Each file's content must use real newline characters and normal indentation "
                "so it is human-readable when opened in an editor (not one long line)."
            ),
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "File name only (basename), e.g. solution.py or __init__.py. "
                            "Must match the final path segment of relative_path."
                        ),
                    },
                    "relative_path": {
                        "type": "string",
                        "description": (
                            "Path of the file relative to the project or session root, "
                            "POSIX-style (slashes only), e.g. src/pkg/module.py or "
                            "challenges/challenge_001_ez/solution.py. No leading slash; "
                            "no '..' segments."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Full text of the file with proper line breaks and indentation "
                            "throughout (e.g. PEP 8-style layout for Python), never a single "
                            "minified line unless the file type truly calls for it. For "
                            "source code: raw statements and comments only; no markdown code "
                            "fences unless the file format requires them (e.g. a .md file)."
                        ),
                    },
                },
                "required": ["name", "relative_path", "content"],
            },
        },
        "notes": {
            "type": "string",
            "description": "Optional short note about the generated files or design choices.",
        },
    },
    "required": ["files"],
}


def _mime_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    suf = path.suffix.lower()
    if suf in (".py", ".pyi", ".pyw"):
        return "text/x-python"
    if suf in (".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".htm"):
        return "text/plain"
    return "application/octet-stream"


def build_user_parts(
    prompt: str,
    attachments: Sequence[Path | str] | None = None,
) -> list[dict[str, Any]]:
    """
    Build Gemini ``contents[0].parts``: one text part plus optional ``inline_data`` parts.

    Each attachment is read from disk and sent as base64 ``inline_data`` (suitable for
    PDFs, images, UTF-8 text files, etc.). Keep total payload within the model's size limits.
    """
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if not attachments:
        return parts
    for raw in attachments:
        path = Path(raw).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"attachment not a file: {path}")
        blob = path.read_bytes()
        b64 = base64.standard_b64encode(blob).decode("ascii")
        parts.append(
            {
                "inline_data": {
                    "mime_type": _mime_for_path(path),
                    "data": b64,
                }
            }
        )
    return parts


class GeminiSimpleAPI:
    """Minimal Gemini REST client for `generateContent`."""

    def __init__(
        self,
        *,
        api_key_file: Path | str,
        model: str,
        working_dir: Path | str,
        protected_directories: Sequence[Path | str] | None = None,
    ) -> None:
        self.set_model(model)
        self._api_key = self._load_api_key(api_key_file)
        self._working_dir = self._ensure_working_dir(working_dir)
        self.set_protected_directories(protected_directories)

    ## Input validators ########################################################
    @staticmethod
    def _ensure_working_dir(working_dir: Path | str) -> Path:
        if isinstance(working_dir, str):
            working_dir = Path(working_dir)
        if working_dir.is_dir():
            return working_dir
        try:
            working_dir.mkdir(parents=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create working directory: {e}") from e
        return working_dir

    @staticmethod
    def _load_api_key(api_key_file: Path | str) -> str:
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_key:
            return env_key
        if not isinstance(api_key_file, Path):
            api_key_file = Path(api_key_file)
        if not api_key_file.is_file():
            raise FileNotFoundError(
                f"Missing API key: set GEMINI_API_KEY or create {api_key_file}"
            )
        data = json.loads(api_key_file.read_text(encoding="utf-8"))
        key = data.get("api_key", "").strip()
        if not key:
            raise ValueError(f"api_key missing or empty in {api_key_file}")
        return key

    ## Getters and setters #####################################################
    def get_model(self) -> str:
        return self._model
    
    def get_working_dir(self) -> Path:
        return self._working_dir
    
    def get_protected_directories(self) -> Sequence[Path]:
        return self._protected_directories

    def set_model(self, model: str) -> None:
        if model not in MODEL_LIST:
            raise ValueError(f"Unknown model: {model}")
        self._model = model
    
    def set_working_dir(self, working_dir: Path) -> None:
        self._working_dir = self._ensure_working_dir(working_dir)

    def set_protected_directories(self, protected_directories: Sequence[Path | str]) -> None:
        self._protected_directories = protected_directories


    ## URL handlers ############################################################
    def _endpoint(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-goog-api-key": self._api_key,
        }

    def _post_generate(self, body_obj: dict[str, Any]) -> dict:
        body = json.dumps(body_obj).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint(),
            data=body,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e

    ## Content handlers ########################################################
    def generate_content_structured(
        self,
        prompt: str,
        *,
        attachments: Sequence[Path | str] | None = None,
    ) -> dict[str, Any]:
        """
        Return parsed JSON matching the multifile schema (``files`` + optional ``notes``).

        ``attachments`` — optional paths to files on disk; each is appended to the user turn
        as ``inline_data`` (base64) after the text ``prompt``, for multimodal models.
        """
        parts = build_user_parts(prompt, attachments)
        payload = self._post_generate(
            {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": MULTIFILE_RESPONSE_SCHEMA,
                },
            }
        )
        text = self._text_from_response(payload)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model did not return valid JSON: {text!r}") from e

    @staticmethod
    def _text_from_response(payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Unexpected response: {json.dumps(payload, indent=2)}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        return "".join(texts).strip()

    ## File management #########################################################
    def write_files(self, files: list[dict[str, Any]]) -> list[Path]:
        path_list = []
        for file in files:
            path = self._working_dir / file["relative_path"]

            # Check if the parent directory is protected (!)
            if path.parent in self.get_protected_directories():
                path = self._working_dir / "illegal_file.py"
                path.write_text(f"print(\"You must not try to write to protected directory: {self.get_protected_directories()}\")", encoding="utf-8")
            else:
                path.write_text(file["content"], encoding="utf-8")

            path_list.append(path)
        return path_list

    ## Orchestration method ####################################################
    def prompt(
        self,
        *,
        prompt: str,
        attachments: Sequence[Path | str] | None = None,
        verbose: bool = False,
    ) -> tuple[list[Path], str]:
        """
        Run structured generation, write ``files`` under ``working_dir``, return absolute paths.

        If ``verbose`` is True, also print a short write summary (omit when the caller prints).
        """
        if verbose:
            print(f"Prompt: {prompt}")
        content = self.generate_content_structured(prompt, attachments=attachments)
        files = content["files"]
        notes = content.get("notes", "")
        path_list = self.write_files(files)

        if verbose:
            self.print_report(path_list, notes)

        return (path_list, notes)

    @staticmethod
    def print_report(path_list: list[Path], notes: str) -> None:
        print(f"\nWrote {len(path_list)} files:")
        for path in path_list:
            print(f"  + {path}")
        if notes:
            print(f"\nNotes: {notes}")
