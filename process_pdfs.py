import pdfplumber
import json
import re
import spacy
import nltk
from nltk.corpus import wordnet
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize spaCy and NLTK
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logger.error(f"Failed to load spaCy model: {e}")
    raise
try:
    nltk.download("wordnet", quiet=True)
except Exception as e:
    logger.warning(f"NLTK WordNet download failed, proceeding without synonyms: {e}")

def generate_keywords(task, persona, use_wordnet=False):
    """Generate keywords dynamically from task and persona."""
    logger.info(f"Generating keywords for task: {task}, persona: {persona}")
    task_doc = nlp(task)
    persona_doc = nlp(persona)
    
    # Extract nouns, verbs, adjectives, and named entities
    keywords = set()
    for token in task_doc:
        if token.pos_ in ["NOUN", "VERB", "ADJ"] and not token.is_stop:
            keywords.add(token.text.lower())
    for ent in task_doc.ents:
        keywords.add(ent.text.lower())
    for token in persona_doc:
        if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop:
            keywords.add(token.text.lower())
    
    # Add synonyms using WordNet (if enabled)
    if use_wordnet:
        try:
            task_doc_vec = nlp(task)
            synonyms = set()
            for keyword in keywords.copy():
                for syn in wordnet.synsets(keyword):
                    for lemma in syn.lemas():
                        synonym = lemma.name().lower().replace("_", " ")
                        synonym_doc = nlp(synonym)
                        if synonym_doc.has_vector and task_doc_vec.has_vector:
                            if task_doc_vec.similarity(synonym_doc) > 0.5:
                                synonyms.add(synonym)
            keywords.update(synonyms)
            logger.info(f"Added {len(synonyms)} filtered WordNet synonyms")
        except Exception as e:
            logger.warning(f"WordNet synonym extraction failed: {e}")
    
    keywords = [k for k in keywords if len(k) > 2]
    logger.info(f"Generated {len(keywords)} keywords: {keywords[:10]}...")
    return keywords

def extract_text(pdf_path):
    """Extract text from a PDF and identify sections."""
    if not pdf_path.exists():
        logger.warning(f"Skipping missing PDF: {pdf_path}")
        return []
    sections = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.debug(f"Processing PDF: {pdf_path}")
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split('\n')
                current_section = {
                    "filename": pdf_path.name,
                    "title": "Untitled Section",
                    "text": "",
                    "page_number": page.page_number
                }
                for line in lines:
                    if line.isupper() or (len(line.strip()) < 50 and line.strip()):
                        if current_section["text"]:
                            sections.append(current_section)
                            current_section = {
                                "filename": pdf_path.name,
                                "title": line.strip(),
                                "text": "",
                                "page_number": page.page_number
                            }
                        else:
                            current_section["title"] = line.strip()
                    else:
                        current_section["text"] += line + " "
                if current_section["text"]:
                    sections.append(current_section)
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
    return sections

def filter_and_rank_sections(sections, task, keywords):
    """Filter sections by keywords and rank using spaCy similarity and keyword counts."""
    logger.info(f"Filtering {len(sections)} sections with {len(keywords)} keywords")
    # Keyword-based filtering with relaxed matching
    filtered = []
    for section in sections:
        matches = sum(1 for keyword in keywords if re.search(re.escape(keyword), section["text"], re.IGNORECASE))
        if matches > 0:
            section["keyword_matches"] = matches
            filtered.append(section)
    logger.info(f"Filtered to {len(filtered)} sections")
    
    if not filtered:
        logger.warning("No sections matched keywords")
        return []
    
    # Combined ranking
    task_doc = nlp(task)
    ranked = []
    max_keywords = max(1, len(keywords))
    for section in filtered:
        if section["keyword_matches"] / max_keywords > 0.5:  # Skip NLP for high-match sections
            combined_score = section["keyword_matches"] / max_keywords
        else:
            section_doc = nlp(section["text"][:300])  # Truncate for speed
            spacy_score = task_doc.similarity(section_doc) if section_doc.has_vector else 0.0
            combined_score = 0.5 * spacy_score + 0.5 * (section["keyword_matches"] / max_keywords)
        ranked.append({"section": section, "score": combined_score})
    
    ranked.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"Ranked {len(ranked)} sections, returning top 5")
    return ranked[:5]

def process_collection(collection_dir, output_dir, use_wordnet=False):
    """Process a single collection and generate output JSON."""
    try:
        # Parse input JSON
        input_json_path = collection_dir / "challenge1b_input.json"
        if not input_json_path.exists():
            logger.warning(f"Skipping {collection_dir}: challenge1b_input.json not found")
            return
        logger.info(f"Processing collection: {collection_dir}")
        with open(input_json_path) as f:
            input_data = json.load(f)
        
        # Validate input structure
        required_keys = ["challenge_info", "documents", "persona", "job_to_be_done"]
        if not all(key in input_data for key in required_keys):
            logger.error(f"Invalid input JSON in {collection_dir}")
            return
        
        task = input_data["job_to_be_done"]["task"]
        persona = input_data["persona"]["role"]
        
        # Generate keywords
        keywords = generate_keywords(task, persona, use_wordnet=use_wordnet)
        
        # Extract text from PDFs in parallel
        pdf_paths = [collection_dir / "PDFs" / doc["filename"] for doc in input_data["documents"] if (collection_dir / "PDFs" / doc["filename"]).exists()]
        logger.info(f"Extracting text from {len(pdf_paths)} PDFs")
        with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced for laptop
            all_sections = list(executor.map(extract_text, pdf_paths))
        
        # Flatten sections
        sections = [s for page_sections in all_sections for s in page_sections]
        
        # Filter and rank sections
        ranked_sections = filter_and_rank_sections(sections, task, keywords)
        
        # Generate output JSON
        output = {
            "metadata": {
                "input_documents": [doc["filename"] for doc in input_data["documents"] if (collection_dir / "PDFs" / doc["filename"]).exists()],
                "persona": persona,
                "job_to_be_done": task,
                "processing_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
            },
            "extracted_sections": [
                {
                    "document": section["section"]["filename"],
                    "section_title": section["section"]["title"],
                    "importance_rank": i + 1,
                    "page_number": section["section"]["page_number"]
                } for i, section in enumerate(ranked_sections)
            ],
            "subsection_analysis": [
                {
                    "document": section["section"]["filename"],
                    "refined_text": section["section"]["text"][:500],
                    "page_number": section["section"]["page_number"]
                } for section in ranked_sections
            ]
        }
        
        # Save output in collection-specific folder
        collection_name = collection_dir.name
        collection_output_dir = output_dir / collection_name
        collection_output_dir.mkdir(exist_ok=True)
        output_path = collection_output_dir / "challenge1b_output.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        logger.info(f"Generated output: {output_path}")
        
    except Exception as e:
        logger.error(f"Error processing collection {collection_dir}: {e}")

def main():
    """Main function to process all collections."""
    input_dir = Path("./input")
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    
    start_time = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        collection_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
        logger.info(f"Processing {len(collection_dirs)} collections")
        executor.map(lambda d: process_collection(d, output_dir, use_wordnet=False), collection_dirs)
    
    runtime = time.perf_counter() - start_time
    logger.info(f"Total runtime: {runtime:.2f} seconds")
    if runtime > 10:
        logger.warning("Runtime exceeds 10 seconds, optimization may be needed")

if __name__ == "__main__":
    main()