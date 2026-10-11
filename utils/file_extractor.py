"""
Resume text extraction utilities.

Supports PDF, DOCX, and plain text resume uploads. The extracted text is what
gets passed downstream as the "resume context" for analysis.

Framework-agnostic by design: functions accept a filename + raw bytes (or any
file-like object with .name/.read()), so they work equally well with
Streamlit's UploadedFile, a plain BytesIO, or an open() handle.
"""

import io

import pdfplumber
from docx import Document

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def allowed_file(filename: str) -> bool:
    """Check whether a filename has a supported extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def extract_text_from_upload(uploaded_file) -> str:
    """
    Extract plain text from an uploaded resume file.

    Args:
        uploaded_file: A file-like object with `.name` (or `.filename`) and
            `.read()` / `.getvalue()` - e.g. a Streamlit UploadedFile.

    Returns:
        Extracted plain text content of the resume.

    Raises:
        ValueError: If the file type is unsupported or extraction fails.
    """
    filename = getattr(uploaded_file, "name", None) or getattr(
        uploaded_file, "filename", ""
    )#we can also use filename = uploaded_file.name if we are sure that the uploaded_file will always have a name attribute, but using getattr allows us to provide a default value and avoid potential AttributeError if the name attribute is missing.
    filename = (filename or "").lower()

    if not allowed_file(filename):
        raise ValueError(
            "Unsupported file type. Please upload a .pdf, .docx, or .txt resume."
        )

    if hasattr(uploaded_file, "getvalue"):
        raw_bytes = uploaded_file.getvalue()
    else:
        raw_bytes = uploaded_file.read()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(raw_bytes)
    if filename.endswith(".docx"):
        return extract_text_from_docx_bytes(raw_bytes)
    return extract_text_from_txt_bytes(raw_bytes)


def extract_text_from_pdf_bytes(raw_bytes: bytes) -> str:
    text_chunks = []
    stream = io.BytesIO(raw_bytes)#create a temporary in-memory byte stream from the raw bytes of the PDF file. This allows pdfplumber to read the PDF content without needing to save it to disk first.
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)#append the extracted text from each page to the text_chunks list. This allows us to accumulate the text from all pages of the PDF document.

    text = "\n".join(text_chunks).strip()#join all the extracted text chunks into a single string, separating them with newlines. The strip() method is then called to remove any leading or trailing whitespace from the final text output.
    if not text:
        raise ValueError(
            "Could not extract any text from this PDF. It may be a scanned "
            "image-only document. Please upload a text-based PDF, DOCX, or "
            "paste the resume text directly."
        )
    return text


def extract_text_from_docx_bytes(raw_bytes: bytes) -> str:
    stream = io.BytesIO(raw_bytes)
    document = Document(stream)

    parts = []
    for paragraph in document.paragraphs:
        if paragraph.text and paragraph.text.strip():
            parts.append(paragraph.text.strip())

    # Also pull text out of tables (common in resumes for skills/experience grids).
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                parts.append(row_text)

    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("Could not extract any text from this DOCX file.")
    return text


def extract_text_from_txt_bytes(raw_bytes: bytes) -> str:
    try:
        text = raw_bytes.decode("utf-8")#attempt to decode the raw bytes of the text file using UTF-8 encoding. UTF-8 is a common encoding for text files and can handle a wide range of characters from different languages.
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="ignore")#if the UTF-8 decoding fails (e.g., due to invalid byte sequences), we catch the UnicodeDecodeError and attempt to decode the bytes using Latin-1 encoding instead. The errors="ignore" argument tells Python to ignore any bytes that cannot be decoded in Latin-1, which can help prevent crashes due to encoding issues while still extracting as much text as possible.

    text = text.strip()
    if not text:
        raise ValueError("The uploaded text file is empty.")
    return text
