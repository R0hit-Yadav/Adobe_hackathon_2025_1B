# Challenge 1b: Multi-Collection PDF Analysis Solution

## Overview
This solution for Challenge 1b of the Adobe India Hackathon 2025 processes multiple collections of PDF documents, extracting relevant sections based on personas and tasks. It generates structured JSON outputs in separate folders per collection, runs offline, and is optimized for accuracy and performance.

## Project Structure
```
Challenge_1b/
├── input/
│   ├── Collection 1/
│   │   ├── PDFs/
│   │   └── challenge1b_input.json
│   ├── Collection 2/
│   ├── Collection 3/
├── output/
│   ├── Collection 1/
│   │   └── challenge1b_output.json
│   ├── Collection 2/
│   ├── Collection 3/
├── process_pdfs.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## Dependencies
- **Python**: 3.10
- **Libraries**:
  - `pdfplumber` (0.11.4): PDF text extraction
  - `spacy` (3.7.6) with `en_core_web_sm` (~50 MB): NLP for keyword extraction and ranking
  - `nltk` (3.8.1) with WordNet and punkt (~10 MB): Synonym augmentation and tokenization
- Installed locally or in Docker.

## Setup and Installation
### Local Testing (Without Docker)
1. **Install Python 3.10**:
   - Verify: `python --version`.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   python -m nltk.downloader wordnet punkt
   ```
3. **Prepare Input**:
   - Place PDFs and `challenge1b_input.json` in `input/Collection 1/`, etc.
4. **Run the Script**:
   ```bash
   python process_pdfs.py
   ```
5. **Check Outputs**:
   - Verify `output/Collection 1/challenge1b_output.json`, etc.
   - Check logs for runtime, keywords, and errors.

### Docker Testing
1. **Install Docker**:
   - Verify: `docker --version`.
2. **Build the Image**:
     ```bash
   sudo docker build --platform linux/amd64 -t adobe:hackathon25 .
   ```
3. **Run the Container**:
   ```bash
   sudo docker run --rm   -v $(pwd)/app/input:/app/input   -v $(pwd)/app/output:/app/output   --network none   adobe:hackathon25
   ```
4. **Check Outputs**:
   - Verify `output/Collection 1/challenge1b_output.json`, etc.

## Implementation Details
- **Text Extraction**: Uses `pdfplumber` with font-based heading detection.
- **Keyword Extraction**: Combines task/persona keywords (via `spaCy`) with PDF summary keywords, plus filtered WordNet synonyms.
- **Content Analysis**:
  - Filters sections with stemmed and partial keyword matching.
  - Ranks with 70% keyword-based scoring and 30% `spaCy` similarity.
  - Prioritizes task-relevant PDFs (e.g., "Things to Do" for travel).
- **Output**: Saves `challenge1b_output.json` in `output/<collection_name>/`.
- **Optimization**: Caches summaries and sections, limits NLP, adjusts parallel workers.

## Constraints Addressed
- **Runtime**: Targets < 10 seconds.
- **Model Size**: `en_core_web_sm` (~50 MB) + NLTK (~10 MB) < 200 MB.
- **No Internet**: Offline-compatible.
- **Hardware**: CPU-only, AMD64.
- **PDFs**: Text-based, handles missing files.

## Local Testing Tips
- Verify PDFs match `challenge1b_input.json`.
- Check logs for keyword relevance and section matches.
- Use virtual environment for dependency issues.
- Test with fewer PDFs if runtime is high.

## Troubleshooting
- **Inaccurate Sections**: Check PDF headings in logs; share PDF snippets.
- **Empty Sections**: Verify keywords match PDF content.
- **Runtime > 10 Seconds**: Reduce `max_workers` or PDFs.
- **WordNet Errors**: Reinstall NLTK if synonyms fail.
- **spaCy Warning**: Combined ranking mitigates `en_core_web_sm` limitations.

## Notes
- Assumes JSONs follow Travel Planning sample structure.
- Section detection tuned for expected headings.
- Skips missing files with warnings.

docker build --platform linux/amd64 -t adobe:hackathon25 .

sudo docker run --rm \
  -v $(pwd)/app/input:/app/input \
  -v $(pwd)/app/output:/app/output \
  --network none \
  adobe:hackathon25