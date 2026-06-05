import json
import time
from pathlib import Path

import streamlit as st

from modules.ocr import (
    get_available_kraken_models,
    get_kraken_version,
    kraken_available,
    list_image_files,
    run_kraken_binarize,
    run_kraken_segment,
)
from modules.paths import BASE_DIR, get_step_paths
from modules.project import Project
from steps.utils import render_step_status


def render() -> None:
    st.header("0️⃣ Layout-Segmentierung")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen. Bitte unter 'Projekte' ein Projekt öffnen.")
        return

    if project.settings.get("input_type") != "images":
        st.info(
            "Dieses Projekt verwendet bestehende PAGE-XML-Dateien. "
            "Die Segmentierung wird übersprungen — bitte direkt mit Schritt 1 (Preprocessing) fortfahren."
        )
        return

    render_step_status("step0")

    paths     = get_step_paths(project.project_dir)
    images_dir = paths["source_images"]
    page_dir   = paths["source_page"]

    # ── Tool-Verfügbarkeit ────────────────────────────────────────────────────
    kraken_ok = kraken_available()
    if kraken_ok:
        st.success(f"Kraken: {get_kraken_version() or '(Version unbekannt)'}")
    else:
        st.error("Kraken nicht gefunden — `uv add kraken`")
        st.stop()

    # ── Modell ────────────────────────────────────────────────────────────────
    st.subheader("Segmentierungsmodell")

    model_dir     = BASE_DIR / "models"
    kraken_models = get_available_kraken_models(model_dir)
    ocr_settings  = project.settings.get("ocr", {})

    kraken_options = ["(blla-Standard)"] + [str(m) for m in kraken_models]
    saved_seg      = ocr_settings.get("kraken_segment_model") or "(blla-Standard)"
    seg_index      = kraken_options.index(saved_seg) if saved_seg in kraken_options else 0

    seg_choice = st.selectbox(
        "Kraken Segmentierungsmodell",
        kraken_options,
        index=seg_index,
        help="Eigene .mlmodel-Dateien in ~/pagetodracor/models/ ablegen.",
    )

    # ── Bilddateien ───────────────────────────────────────────────────────────
    st.subheader("Eingabe")
    images = list_image_files(images_dir)

    if images:
        st.info(f"{len(images)} Bild(er) in `{images_dir}` — sortiert nach Dateiname.")
        with st.expander("Dateien anzeigen"):
            for img in images:
                st.text(img.name)
    else:
        st.warning(
            f"Keine Bilddateien in `{images_dir}` gefunden. "
            "Bitte Bilder (jpg/png/tif) dort ablegen."
        )

    # ── Segmentierung starten ─────────────────────────────────────────────────
    st.subheader("Segmentierung")

    if st.button("Segmentierung starten", disabled=len(images) == 0, type="primary"):
        _run_segmentation(
            project=project,
            images=images,
            page_dir=page_dir,
            paths=paths,
            seg_choice=seg_choice,
        )

    # ── Externe OCR / Abschließen ─────────────────────────────────────────────
    st.divider()
    st.subheader("Texterkennung (extern)")

    existing_xmls = sorted(page_dir.glob("*.xml")) if page_dir.exists() else []
    if existing_xmls:
        st.info(
            f"{len(existing_xmls)} PAGE-XML-Datei(en) in `{page_dir}` vorhanden.\n\n"
            "**Externes OCR-Workflow:** Die segmentierten PAGE-XMLs können mit einem "
            "beliebigen OCR-Tool angereichert werden (z.B. Calamari 2.x, Kraken OCR, "
            "OCR4all) und anschließend zurück nach `source/page/` gelegt werden. "
            "Die App liest die TextEquiv-Elemente im nächsten Schritt."
        )
        with st.expander("Vorhandene PAGE-XMLs anzeigen"):
            for xml in existing_xmls:
                has_text = _xml_has_text(xml)
                marker = "📝" if has_text else "📐"
                st.text(f"{marker} {xml.name}{'  (Text vorhanden)' if has_text else '  (nur Layout)'}")

        step_data = project.get_step("step0")
        if step_data["status"] != "done":
            st.info(
                "Sobald die Texterkennung abgeschlossen ist (intern oder extern), "
                "Schritt hier abschließen."
            )
            if st.button("Schritt abschließen", type="primary"):
                _mark_done(project, paths, len(existing_xmls), len(images))
    else:
        st.caption("Noch keine PAGE-XMLs vorhanden — bitte zuerst Segmentierung starten.")


def _xml_has_text(xml_path: Path) -> bool:
    """Prüft, ob eine PAGE-XML TextEquiv-Elemente enthält."""
    try:
        content = xml_path.read_text(encoding="utf-8")
        return "<TextEquiv" in content
    except Exception:
        return False


def _run_segmentation(
    project: Project,
    images: list[Path],
    page_dir: Path,
    paths: dict,
    seg_choice: str,
) -> None:
    page_dir.mkdir(parents=True, exist_ok=True)
    total     = len(images)
    errors: list[str] = []
    seg_model = None if seg_choice == "(blla-Standard)" else Path(seg_choice)

    progress  = st.progress(0, text="Initialisiere Segmentierung...")
    log_area  = st.empty()
    time_area = st.empty()
    start     = time.time()

    for i, img in enumerate(images):
        bin_image = page_dir / (img.stem + ".png")
        page_xml  = page_dir / (img.stem + ".xml")
        elapsed   = time.time() - start
        eta       = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0

        progress.progress(
            (i + 1) / total,
            text=f"Seite {i + 1}/{total}: {img.name}",
        )
        time_area.caption(
            f"Laufzeit: {elapsed:.0f}s — geschätzte Restzeit: {eta:.0f}s"
        )

        log_area.code(f"[Binarize] {img.name}...")
        r = run_kraken_binarize(img, bin_image)
        if r.returncode != 0:
            errors.append(f"Binarize Fehler bei {img.name}: {r.stderr[-300:]}")
            log_area.code(f"[Binarize] FEHLER {img.name}\n{(r.stdout + r.stderr)[-1000:]}")
            continue

        log_area.code(f"[Segment] {img.name}...")
        r = run_kraken_segment(bin_image, page_xml, seg_model)
        log_snippet = (r.stdout + r.stderr)[-1500:]
        log_area.code(f"[Segment] {img.name}\n{log_snippet}")

        if r.returncode != 0:
            errors.append(f"Segment Fehler bei {img.name}: {r.stderr[-300:]}")

    time_area.caption(f"Gesamtlaufzeit: {time.time() - start:.0f}s")
    for err in errors:
        st.warning(err)

    successful = total - len(errors)
    if successful > 0:
        project.save_settings({
            "ocr": {
                "kraken_segment_model": None if seg_choice == "(blla-Standard)" else seg_choice,
            }
        })
        st.success(
            f"Segmentierung abgeschlossen: {successful}/{total} Seiten. "
            f"PAGE-XMLs (ohne Text) in `{page_dir}`."
        )
        st.rerun()
    else:
        st.error("Segmentierung für alle Seiten fehlgeschlagen — bitte Logs prüfen.")


def _mark_done(project: Project, paths: dict, xml_count: int, image_count: int) -> None:
    marker = paths["step0"]
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "xmls_available": xml_count,
                "images_total": image_count,
                "ocr_method": "external",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    project.save_step("step0", marker, {
        "xmls_available": xml_count,
        "images_total": image_count,
        "ocr_method": "external",
    })
    st.success("Schritt 0 abgeschlossen. Weiter mit Schritt 1 (Preprocessing).")
    st.rerun()
