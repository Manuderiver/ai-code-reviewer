# 🤖 AI Code Reviewer

Bot de revisión de código en Python que usa la **API de Google Gemini** para
analizar archivos `.py` o el `git diff` de un repositorio, detectando bugs
potenciales, code smells y sugerencias de mejora. Genera un reporte en
Markdown listo para compartir o pegar en un Pull Request.

Usa el tier gratuito de la API de Gemini (sin tarjeta de crédito, sin costo).

## ✨ Características

- **Revisión de un archivo** puntual (`--file`)
- **Revisión de un directorio completo** de forma recursiva (`--dir`)
- **Revisión del `git diff`** de cambios no commiteados (`--diff`), ideal antes
  de un commit o PR
- Reporte estructurado en Markdown, clasificando cada observación como
  `BUG`, `SMELL` o `MEJORA`
- Manejo de errores robusto (archivo no encontrado, API key faltante, errores
  de la API, timeout, git no instalado, etc.)
- Diseño orientado a objetos: `GeminiClient` (comunicación con el modelo) y
  `CodeReviewer` (orquestación) están desacoplados, lo que facilita testear o
  cambiar de proveedor de LLM en el futuro

## 🏗️ Arquitectura

```
CodeReviewer ──uses──> GeminiClient ──API──> Google Gemini (gemini-2.5-flash)
     │
     ├─ review_file()       -> ReviewResult
     ├─ review_directory()  -> List[ReviewResult]
     └─ review_git_diff()   -> ReviewResult
                │
                v
          build_report() -> Markdown
```

## 🛠️ Tecnologías utilizadas

- **Python 3.10+**
- **Google Gemini API** (`gemini-2.5-flash`) vía el SDK oficial `google-genai`
- **argparse** — interfaz de línea de comandos
- **dataclasses** — modelado de resultados
- POO: clases, encapsulamiento y excepciones personalizadas
  (`GeminiConfigError`, `CodeReviewError`)

## 📦 Instalación

1. Conseguir una API key **gratuita** de Gemini en
   [Google AI Studio](https://aistudio.google.com/apikey) (con tu cuenta de
   Google, sin tarjeta de crédito)

2. Clonar este repositorio e instalar dependencias:
   ```bash
   git clone https://github.com/Manuderiver/ai-code-reviewer.git
   cd ai-code-reviewer
   pip install -r requirements.txt
   ```

3. Configurar la API key como variable de entorno:
   ```bash
   export GEMINI_API_KEY="tu-api-key-aca"
   ```

## 🚀 Uso

```bash
# Revisar un archivo puntual
python code_reviewer.py --file examples/ejemplo_con_bugs.py

# Revisar todos los .py de un directorio
python code_reviewer.py --dir mi_proyecto/

# Revisar los cambios pendientes de commitear
python code_reviewer.py --diff

# Guardar el reporte en otra ruta
python code_reviewer.py --file archivo.py --output mi_reporte.md
```

## 📄 Ejemplo de salida

Corriendo el bot sobre [`examples/ejemplo_con_bugs.py`](examples/ejemplo_con_bugs.py)
(un archivo con errores intencionales), el resultado es:

> Ver [`examples/reporte_ejemplo.md`](examples/reporte_ejemplo.md)

```markdown
## `examples/ejemplo_con_bugs.py`

- [BUG] La función `dividir` no controla el caso `b == 0`...
- [BUG] `buscar_usuario` no maneja el caso en que el usuario no existe...
- [SMELL] En `Contador`, `total` está declarado como atributo de clase...
- [BUG] `leer_archivo` abre el archivo sin usar `with`...
- [MEJORA] Agregar type hints y docstrings...
```

## 🔭 Posibles mejoras futuras

- Integración como pre-commit hook para bloquear commits con bugs graves
- Soporte para más lenguajes además de Python
- GitHub Action que comente automáticamente en cada Pull Request
- Cache de resultados para no reprocesar archivos sin cambios

## Autor

**Aguilar Juan Manuel** — [GitHub](https://github.com/Manuderiver)
