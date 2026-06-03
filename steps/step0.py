import json
import time
from pathlib import Path

import streamlit as st

from modules.ocr import (
    calamari_available,
    get_available_calamari_checkpoints,
    get_available_kraken_models,
    get_calamari_version,
    get_kraken_version,
    kraken_available,
    list_image_files,
    run_calamari_predict,
    run_kraken_binarize_segment,
)
from modules.paths import BASE_DIR, get_step_paths
from modules.project import Project
from steps.utils import render_step_status


def render() -> None:
    st.header("0️⃣ OCR-Pipeline")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen. Bitte unter 'Projekte' ein Projekt öffnen.")
        return

    if project.settings.get("input_type") != "images":
        st.info(
            "Dieses Projekt verwendet bestehende PAGE-XML-Dateien. "
            "Die OCR-Pipeline wird übersprungen — bitte direkt mit Schritt 1 (Preprocessing) fortfahren."
        )
        return

    render_step_status("step0")

    # ── Tool-Verfügbarkeit ────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    kraken_ok   = kraken_available()
    calamari_ok = calamari_available()

    with col1:
        if kraken_ok:
            st.success(f"Kraken: {get_kraken_version() or '(Version unbekannt)'}")
        else:
            st.error("Kraken nicht gefunden — `pip install kraken`")
    with col2:
        if calamari_ok:
            st.success(f"Calamari: {get_calamari_version() or '(Version unbekannt)'}")
        else:
            st.error("Calamari nicht gefunden — `pip install calamari-ocr`")

    if not (kraken_ok and calamari_ok):
        st.stop()

    # ── Modellpfade ───────────────────────────────────────────────────────────
    st.subheader("Modelle")

    model_dir = BASE_DIR / "models"
    ocr_settings = project.settings.get("ocr", {})

    kraken_models    = get_available_kraken_models(model_dir)
    calamari_models  = get_available_calamari_checkpoints(model_dir)

    kraken_options   = ["(blla-Standard)"] + [str(m) for m in kraken_models]
    saved_seg        = ocr_settings.get("kraken_segment_model") or "(blla-Standard)"
    seg_index        = kraken_options.index(saved_seg) if saved_seg in kraken_options else 0

    calamari_options = [str(m) for m in calamari_models]
    saved_cal        = ocr_settings.get("calamari_checkpoint") or ""
    cal_index        = calamari_options.index(saved_cal) if saved_cal in calamari_options else 0

    col_seg, col_cal = st.columns(2)
    with col_seg:
        if kraken_options:
            seg_choice = st.selectbox(
                "Kraken Segmentierungsmodell",
                kraken_options,
                index=seg_index,
                help="Eigene .mlmodel-Dateien in ~/pagetodracor/models/ ablegen.",
            )
        else:
            seg_choice = "(blla-Standard)"
            st.info("Keine eigenen Kraken-Modelle in `~/pagetodracor/models/` gefunden — blla-Standard wird verwendet.")

    with col_cal:
        if calamari_options:
            cal_choice = st.selectbox(
                "Calamari Checkpoint",
                calamari_options,
                index=cal_index,
                help="Calamari-Checkpoints (Ordner mit *.ckpt.json) in ~/pagetodracor/models/ ablegen.",
            )
        else:
            cal_choice = ""
            st.warning(
                "Kein Calamari-Checkpoint gefunden. "
                "Checkpoint-Ordner in `~/pagetodracor/models/` ablegen oder Pfad manuell eingeben."
            )

    manual_cal = st.text_input(
        "Calamari Checkpoint — manueller Pfad (überschreibt Auswahl oben)",
        value="",
        placeholder="/pfad/zum/checkpoint",
    )
    calamari_path = manual_cal.strip() if manual_cal.strip() else cal_choice

    # ── Bilddateien ───────────────────────────────────────────────────────────
    st.subheader("Eingabe")
    paths      = get_step_paths(project.project_dir)
    images_dir = paths["source_images"]
    page_dir   = paths["source_page"]
    images     = list_image_files(images_dir)

    if images:
        st.info(f"{len(images)} Bild(er) in `{images_dir}` — sortiert nach Dateiname.")
        with st.expander("Dateien anzeigen"):
            for img in images:
                st.text(img.name)
    else:
        st.warning(f"Keine Bilddateien in `{images_dir}` gefunden. Bitte Bilder (jpg/png/tif) dort ablegen.")

    # ── OCR starten ──────────────────────────────────────────────────────────
    st.subheader("Verarbeitung")

    can_start = len(images) > 0 and bool(calamari_path)
    if not can_start and len(images) > 0:
        st.warning("Bitte einen Calamari-Checkpoint angeben, um die OCR zu starten.")

    if st.button("OCR starten", disabled=not can_start, type="primary"):
        _run_ocr(
            project=project,
            images=images,
            page_dir=page_dir,
            paths=paths,
            seg_choice=seg_choice,
            calamari_path=calamari_path,
        )


def _run_ocr(
    project: Project,
    images: list[Path],
    page_dir: Path,
    paths: dict,
    seg_choice: str,
    calamari_path: str,
) -> None:
    page_dir.mkdir(parents=True, exist_ok=True)
    total  = len(images)
    errors: list[str] = []

    seg_model = None if seg_choice == "(blla-Standard)" else Path(seg_choice)

    progress  = st.progress(0, text="Initialisiere OCR-Pipeline...")
    log_area  = st.empty()
    time_area = st.empty()
    start     = time.time()

    for i, img in enumerate(images):
        page_xml = page_dir / (img.stem + ".xml")
        elapsed  = time.time() - start
        eta      = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0

        progress.progress(
            (i + 1) / total,
            text=f"Seite {i + 1}/{total}: {img.name}",
        )
        time_area.caption(
            f"Laufzeit: {elapsed:.0f}s — geschätzte Restzeit: {eta:.0f}s"
        )

        # Schritt 1: Kraken — Binarisierung + Segmentierung
        log_area.code(f"[Kraken] {img.name} — Segmentierung läuft...")
        r = run_kraken_binarize_segment(img, page_xml, seg_model)
        log_snippet = (r.stdout + r.stderr)[-1500:]
        log_area.code(f"[Kraken] {img.name}\n{log_snippet}")

        if r.returncode != 0:
            errors.append(f"Kraken Fehler bei {img.name}: {r.stderr[-300:]}")
            continue

        # Schritt 2: Calamari — Texterkennung
        log_area.code(f"[Calamari] {img.name} — Texterkennung läuft...")
        r = run_calamari_predict(page_xml, Path(calamari_path))
        log_snippet = (r.stdout + r.stderr)[-1500:]
        log_area.code(f"[Calamari] {img.name}\n{log_snippet}")

        if r.returncode != 0:
            errors.append(f"Calamari Fehler bei {img.name}: {r.stderr[-300:]}")

    time_area.caption(f"Gesamtlaufzeit: {time.time() - start:.0f}s")

    for err in errors:
        st.warning(err)

    successful = total - len(errors)
    if successful > 0:
        # Marker-Datei als step0-Output
        marker = paths["step0"]
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps(
                {"images_processed": successful, "images_total": total},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        project.save_step("step0", marker, {
            "images_processed": successful,
            "images_total": total,
        })
        project.save_settings({
            "ocr": {
                "kraken_segment_model": None if seg_choice == "(blla-Standard)" else seg_choice,
                "calamari_checkpoint": calamari_path,
            }
        })
        st.success(
            f"OCR abgeschlossen: {successful}/{total} Seiten erfolgreich. "
            f"PAGE-XML-Dateien in `{page_dir}`."
        )
        st.rerun()
    else:
        st.error("OCR für alle Seiten fehlgeschlagen — bitte Logs prüfen.")
