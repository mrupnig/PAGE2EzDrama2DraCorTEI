from pathlib import Path

import streamlit as st

from modules.paths import get_step_paths
from modules.project import Project
from steps.utils import render_step_status


def render() -> None:
    st.markdown("---")
    st.header("5️⃣ Gesamttext bereinigen")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen.")
        return

    render_step_status("step5")

    paths = get_step_paths(project.project_dir)
    file_in  = paths["step4"]
    file_out = paths["step5"]

    # Letzten Wert aus project.json als Default
    saved_keep = project.get_step("step5")["state"].get("keep_linebreaks", False)
    keep_linebreaks = st.checkbox("Zeilenumbrüche behalten", value=saved_keep)

    if st.button("Gesamttext bereinigen"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 4 ausführen.")
            return
        lines = file_in.read_text(encoding="utf-8").splitlines(keepends=True)

        def normalize_text(text: str) -> str:
            replacements = {
                "ſ": "s",   "ʒ": "z",   "Ʒ": "Z",
                "aͤ": "ä",  "oͤ": "ö",  "uͤ": "ü",
                "Jch": "Ich", "Jtzt": "Itzt", "Jst": "Ist",
                "Jn": "In",  "Jm": "Im",  "Jhm": "Ihm",
                "Jhn": "Ihn", "Jhr": "Ihr", "Jr": "Ir",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text

        if keep_linebreaks:
            cleaned_lines: list[str] = []
            i = 0
            while i < len(lines):
                raw = lines[i].rstrip("\n")
                if raw.strip() == "":
                    cleaned_lines.append("")
                    i += 1
                    continue
                line = raw.strip()
                if line.startswith("~"):
                    cleaned_lines.append(normalize_text(line))
                    i += 1
                    continue
                if line.startswith("@"):
                    cleaned_lines.append(line)
                    i += 1
                    continue
                if line.startswith("$"):
                    cleaned_lines.append("$" + line[1:].strip())
                    i += 1
                    continue
                if line.startswith(("#", "^")):
                    cleaned_lines.append(line)
                    i += 1
                    continue
                cleaned_lines.append(line)
                i += 1
            cleaned_lines = [normalize_text(l) if l else "" for l in cleaned_lines]

        else:
            cleaned_lines = []
            buffer = ""
            verse_mode = False

            def process_line(line: str) -> tuple[str, bool]:
                line = line.rstrip()
                if line.endswith("-") and not line.endswith(" -") and not line.endswith("--"):
                    return line[:-1], True
                return line, False

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                if line.startswith("~"):
                    verse_mode = True
                    if buffer:
                        cleaned_lines.append(buffer.strip())
                        buffer = ""
                    cleaned_lines.append(normalize_text(line.strip()))
                    i += 1
                    continue

                if verse_mode:
                    if not line.startswith(("@", "#", "^", "$", "~", "(")):
                        cleaned_lines.append(normalize_text(line.strip()))
                        i += 1
                        continue
                    else:
                        verse_mode = False

                if line.startswith("@"):
                    verse_mode = False
                    if buffer:
                        cleaned_lines.append(buffer.strip())
                        buffer = ""
                    speaker_line = line
                    i += 1
                    if i < len(lines):
                        next_line = lines[i].strip()
                        if next_line.startswith("(") and next_line.endswith(")"):
                            speaker_line += f" {next_line}"
                            i += 1
                    cleaned_lines.append(speaker_line)
                    continue

                if line.startswith("$"):
                    verse_mode = False
                    combined_line, is_hyphenated = process_line(line[1:].strip())
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith("$"):
                        next_content = lines[i].strip()[1:].strip()
                        processed_next, next_is_hyphenated = process_line(next_content)
                        combined_line += processed_next if is_hyphenated else " " + processed_next
                        is_hyphenated = next_is_hyphenated
                        i += 1
                    if buffer:
                        cleaned_lines.append(buffer.strip())
                        buffer = ""
                    cleaned_lines.append("$" + combined_line.strip())
                    continue

                if line.startswith(("#", "^")):
                    verse_mode = False
                    if buffer:
                        cleaned_lines.append(buffer.strip())
                        buffer = ""
                    cleaned_lines.append(line)
                    i += 1
                    continue

                processed_line, is_hyphenated = process_line(line)
                buffer += " " + processed_line
                while is_hyphenated and i + 1 < len(lines):
                    i += 1
                    next_line = lines[i].strip()
                    processed_line, is_hyphenated = process_line(next_line)
                    buffer += processed_line
                i += 1

            if buffer:
                cleaned_lines.append(buffer.strip())
            cleaned_lines = [normalize_text(l) for l in cleaned_lines]

        file_out.parent.mkdir(parents=True, exist_ok=True)
        file_out.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")

        project.save_step("step5", file_out, {"keep_linebreaks": keep_linebreaks})

        st.success(f"Bereinigter Text gespeichert: {file_out}")
