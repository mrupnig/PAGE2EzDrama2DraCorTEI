# PAGE → EzDrama → DraCor-TEI

An interactive **Streamlit application** for the step-by-step transformation of **PAGE-XML** files into **DraCor-compatible TEI documents**.  
The app guides users through the entire processing chain — from text-line extraction to speaker normalization and final text cleaning.

🔗 **Live App:** [Open in Streamlit Cloud](https://page2ezdrama2dracortei.streamlit.app/)


## Overview

This project is designed to assist researchers, editors, and students in **Digital Humanities**, **text encoding**, **theatre philology** aswell as anybody interested in the digitization process of dramatic plays from scan data to TEI-XML.
It provides a graphical workflow for converting OCR-derived PAGE-XML files into clean, structured TEI suitable for [**DraCor**](https://dracor.org/).


## Features

- Import **PAGE-XML** files (locally or via upload)
    - For detailed information on the PAGE-XML structure and region conventions, see the [Processing Guidelines](docs/guidelines.md).
- Extract and preprocess `TextLine` content
- Detect and manually correct speaker lines
- Normalize speaker variants and faulty OCR data 
    - (e.g., `Georg`,`Ceorg` or `G org` → `@Georg.`)
- Clean and standardize the full text (ligatures, long-s, etc.)
- Optional: preserve original line breaks
- Export ready-to-use text and TEI outputs


## Usage Guide (Workflow)

1. **Select data source** — upload a local ZIP folder or a batch of XML files.
2. **Enter metadata** — title, subtitle, author information.  
3. **Extract bracket lines** — review stage directions and edit manually.  
4. **Find overlooked speakers** — automatic detection and correction.  
5. **Normalize speakers** — merge variant spellings into consistent forms.  
6. **Clean full text** — normalize characters and structure; optionally keep line breaks.  
7. **Export** — download the final TEI file.


## Related Work and Acknowledgements

This application was developed **from scratch** as an independent redesign of earlier workflows for transforming PAGE-XML into TEI-encoded drama texts.  
It draws conceptual inspiration from the earlier project **[PAGEtoTEI](https://github.com/dennerlein/Dramendigitalisierung-PAGEtoTEI)**, which explored a different approach to the PAGE → TEI conversion process.

The present app adopts a new architecture and interaction model built around the **[EzDrama Parser](https://github.com/dracor-org/ezdrama)**, with an entirely reworked pipeline, user interface, and preprocessing logic. The parser is used here to extract, structure, and convert dramatic texts into a DraCor-TEI-compliant format.


## Local Installation

If you want to run the app locally, clone the repository and install all requirements:

```
pip install -r requirements.txt
streamlit run app.py
```
