FROM --platform=linux/amd64 python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -m nltk.downloader wordnet
COPY process_pdfs.py .
CMD ["python", "process_pdfs.py"]