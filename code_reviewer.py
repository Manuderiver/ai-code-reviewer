#!/usr/bin/env python3
"""
AI Code Reviewer
-----------------
Bot de revisión de código que usa la API de Google Gemini para analizar
archivos Python o el `git diff` de un repositorio, y genera un reporte en
Markdown con bugs potenciales, code smells y sugerencias de mejora.

Uso:
    python code_reviewer.py --file ruta/al/archivo.py
    python code_reviewer.py --dir ruta/al/proyecto
    python code_reviewer.py --diff              # revisa el git diff del repo actual

Requiere una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey),
seteada como variable de entorno:
    export GEMINI_API_KEY="tu-api-key-aca"
"""

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from google import genai
from google.genai import errors as genai_errors


# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------

DEFAULT_MODEL = "gemini-2.5-flash"  # rápido y dentro del tier gratuito

SYSTEM_PROMPT = """Sos un revisor de código senior. Analizá el siguiente código \
y respondé ÚNICAMENTE con una lista de observaciones en este formato, una por línea:

- [BUG|SMELL|MEJORA] Descripción breve y concreta de la observación.

No repitas el código. No agregues explicaciones fuera de esa lista. \
Si el código está bien y no hay nada relevante que señalar, respondé:
- [OK] No se detectaron problemas relevantes.
"""


# ----------------------------------------------------------------------
# Excepciones propias
# ----------------------------------------------------------------------

class GeminiConfigError(Exception):
    """Se lanza cuando falta la API key o hay un problema de configuración."""


class CodeReviewError(Exception):
    """Error genérico durante el proceso de revisión."""


# ----------------------------------------------------------------------
# Modelo de datos
# ----------------------------------------------------------------------

@dataclass
class ReviewResult:
    """Representa el resultado de revisar un archivo o diff."""
    target: str
    observations: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        return self.error is not None


# ----------------------------------------------------------------------
# Cliente de Gemini
# ----------------------------------------------------------------------

class GeminiClient:
    """Encapsula la comunicación con la API de Google Gemini."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise GeminiConfigError(
                "No se encontró GEMINI_API_KEY. Conseguí una gratis en "
                "https://aistudio.google.com/apikey y exportala como variable "
                "de entorno: export GEMINI_API_KEY='tu-key'"
            )
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def ask(self, prompt: str) -> str:
        """Envía un prompt al modelo y devuelve la respuesta en texto plano."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"system_instruction": SYSTEM_PROMPT},
            )
        except genai_errors.APIError as exc:
            raise CodeReviewError(f"Error de la API de Gemini: {exc}") from exc
        except Exception as exc:  # errores de red u otros no previstos
            raise CodeReviewError(f"Error inesperado llamando a Gemini: {exc}") from exc

        text = getattr(response, "text", None)
        if not text:
            raise CodeReviewError("Gemini devolvió una respuesta vacía.")
        return text.strip()


# ----------------------------------------------------------------------
# Revisor de código
# ----------------------------------------------------------------------

class CodeReviewer:
    """Orquesta la revisión de archivos o diffs usando un GeminiClient."""

    MAX_CHARS_PER_REQUEST = 15000  # Gemini soporta contexto grande, pero acotamos igual

    def __init__(self, client: GeminiClient):
        self.client = client

    def review_file(self, path: Path) -> ReviewResult:
        """Revisa un único archivo de código."""
        result = ReviewResult(target=str(path))
        try:
            code = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            result.error = f"No se pudo leer el archivo: {exc}"
            return result

        if not code.strip():
            result.observations = ["- [OK] Archivo vacío, nada que revisar."]
            return result

        code = code[: self.MAX_CHARS_PER_REQUEST]
        prompt = f"Archivo: {path.name}\n\n```python\n{code}\n```"

        try:
            raw_response = self.client.ask(prompt)
        except (GeminiConfigError, CodeReviewError) as exc:
            result.error = str(exc)
            return result

        result.observations = self._parse_observations(raw_response)
        return result

    def review_directory(self, directory: Path) -> List[ReviewResult]:
        """Revisa todos los archivos .py de un directorio (excluye .git y venv)."""
        results = []
        py_files = sorted(directory.rglob("*.py"))
        py_files = [f for f in py_files if ".git" not in f.parts and "venv" not in f.parts]

        if not py_files:
            raise CodeReviewError(f"No se encontraron archivos .py en {directory}")

        for file_path in py_files:
            results.append(self.review_file(file_path))
        return results

    def review_git_diff(self, repo_path: Path = Path(".")) -> ReviewResult:
        """Revisa el `git diff` de cambios no commiteados en el repo."""
        try:
            diff_output = subprocess.run(
                ["git", "diff"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            raise CodeReviewError(f"Error ejecutando git diff: {exc}") from exc
        except FileNotFoundError as exc:
            raise CodeReviewError("Git no está instalado o no se encuentra en el PATH.") from exc

        result = ReviewResult(target="git diff")
        if not diff_output.strip():
            result.observations = ["- [OK] No hay cambios pendientes para revisar."]
            return result

        diff_output = diff_output[: self.MAX_CHARS_PER_REQUEST]
        prompt = f"Revisá el siguiente git diff:\n\n```diff\n{diff_output}\n```"

        try:
            raw_response = self.client.ask(prompt)
        except (GeminiConfigError, CodeReviewError) as exc:
            result.error = str(exc)
            return result

        result.observations = self._parse_observations(raw_response)
        return result

    @staticmethod
    def _parse_observations(raw_response: str) -> List[str]:
        lines = [line.strip() for line in raw_response.splitlines() if line.strip()]
        observations = [line for line in lines if line.startswith("-")]
        return observations if observations else [f"- {raw_response}"]


# ----------------------------------------------------------------------
# Generación de reporte
# ----------------------------------------------------------------------

def build_report(results: List[ReviewResult]) -> str:
    """Arma un reporte en Markdown a partir de los resultados de revisión."""
    lines = ["# 🤖 Reporte de Revisión de Código\n"]

    for result in results:
        lines.append(f"## `{result.target}`\n")
        if result.has_error:
            lines.append(f"⚠️ **Error:** {result.error}\n")
            continue
        lines.extend(result.observations)
        lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bot de revisión de código con la API de Google Gemini."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Ruta a un archivo .py a revisar")
    group.add_argument("--dir", type=str, help="Ruta a un directorio con archivos .py")
    group.add_argument("--diff", action="store_true", help="Revisar el git diff actual")
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Modelo de Gemini a usar (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--output", type=str, default="reporte_revision.md",
        help="Archivo de salida para el reporte (default: reporte_revision.md)"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        client = GeminiClient(model=args.model)
    except GeminiConfigError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1

    reviewer = CodeReviewer(client)

    try:
        if args.file:
            results = [reviewer.review_file(Path(args.file))]
        elif args.dir:
            results = reviewer.review_directory(Path(args.dir))
        else:
            results = [reviewer.review_git_diff()]
    except CodeReviewError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report = build_report(results)
    Path(args.output).write_text(report, encoding="utf-8")

    print(report)
    print(f"\n✅ Reporte guardado en: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
