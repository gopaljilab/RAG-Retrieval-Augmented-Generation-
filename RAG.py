import streamlit as st
import os
from typing import Optional
from io import BytesIO
from google import genai
from google.genai.errors import APIError

#Document parser section

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


#Extracts text content from various files types
def read_document_content(uploaded_file):

    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    try:

        if file_extension in ['.txt', '.md']:
            return uploaded_file.getvalue().decode("utf-8")

        elif file_extension == '.pdf':
            if not PdfReader:
                return f"Error : Cannot read PDF. please install pypdf."

            reader = PdfReader(uploaded_file)
            text = ""

            for page in reader.pages:
                text += page.extract_text() or ""  # Handle pages with no extractable text

            return text

        elif file_extension == '.docx':
            if not Document:
                return f"Error : Cannot read DOCX. please install python-docx."

            doc = Document(BytesIO(uploaded_file.getvalue()))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text

        else:
            return f"Error Unsupported file type : {file_extension}"

    except Exception as e:
        return f"Error reading file content: {e}"


# --- Configuration

API_KEY = "AIzaSyD1Jz8DtfIOj26ySOVvcltw__tJ0g2DuyI"   # FIXED: replaced invalid API-KEY

MODEL_NAME = "gemini-2.0-flash"   # gemini-2.5-flash-lite does not exist


class GeminiAPI:

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def generate_content(self, model: str, contents: list, system_instruction: str) -> str:

        try:

            client = genai.Client(api_key=self.api_key)

            config = genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )

            response = client.models.generate_content(
                model=model, 
                contents=contents,
                config=config
            )

            return response.text

        except APIError as e:
            return f"Error during live API call: A Gemini API Error occured. Details: {e}"

        except Exception as e:
            return f"Error during live API call: A Unexpected Error occured. Details: {e}"


#Streamlit Ui and Logic

st.set_page_config(page_title="Gemini RAG Workshop", layout="wide")
st.title("First RAG Sytem: Contextual QA with Gemini")

st.markdown("""
            This Application demonstrates the core concept of **Retrieval-Argumented Genaration (RAG).**
            The LLM(Gemini) is forced to answer your questions *only* by referencing the document you provide.

            supported file types: `text`, `.md`, `.pdf`, and `.docx`.
""")

#Initialize session state for file content and response

if 'uploaded_text' not in st.session_state:
    st.session_state.uploaded_text = ""

#change reg_response to a dictionary to store both the prompt and the answer

if 'rag_response' not in st.session_state:
    st.session_state.rag_response = {}

#Initialize the key for the text area

if 'user_prompt_input' not in st.session_state:
    st.session_state.user_prompt_input = ""

# 1) Browse Button to Load data source

uploaded_file = st.file_uploader(
    "1. Upload Your Data Source(TXT, MD, PDF, or DOCX)",
    type=['txt', 'md', 'pdf', 'docx'],  # FIXED: "text" → "txt"
    help="Upload a Document that Gemini must reference to answer your questions."
)

if uploaded_file is not None:

    file_contents = read_document_content(uploaded_file)

    if isinstance(file_contents, str) and file_contents.startswith("Error"):
        st.error(file_contents)
        st.session_state.uploaded_text = ""
        st.stop()

    else:
        st.session_state.uploaded_text = file_contents
        st.success(f"File **'{uploaded_file.name}'** loaded successfully! ({len(file_contents)} characters)" )

        with st.expander("Review Extracted Document Text"):
            display_text = file_contents[:2000] + ('\n[... Truncated for display ...]' if len(file_contents) > 2000 else '')
            st.code(display_text, language='text')

if not st.session_state.uploaded_text:
    st.info("please upload a supported file type to enable the Q&A section.")
    st.stop()

# 2) TextBox for user Prompt

st.subheader("2. Ask a Question Grounded in the Document")

st.text_area(
    "Enter your question here:",
    placeholder="e.g. What is the main purpose of first paragraph?",
    height=100,
    key="user_prompt_input"
)

#Initilize the API handler
gemini_api = GeminiAPI(api_key=API_KEY)


def run_rag_query():

    current_prompt = st.session_state.get('user_prompt_input', '').strip()

    if not current_prompt:
        st.error("Pleae enter a question")
        return

    if not st.session_state.uploaded_text:
        st.error("Please upload a document first.")
        return

    st.session_state.rag_response = {'prompt': current_prompt, 'answer': None}

    with st.spinner(f"Argumenting Generation for: '{current_prompt[:50]}...'"):

        system_instruction = (
            "You are an expert Q&A system. Your role task is to extract or summerize "
            "Information to answer the user's question. DO NOT user external Knowladge. "
            "Only use the text provided in the 'Context part of the Prompt. "
            "If the answer is not present in the document, you MUSt repky with: "
            "'I cannot find the answer in the provided document.'"
        )

        contents_payload = [
        {"role": "user","parts": [{"text": st.session_state.uploaded_text}]},
        {"role": "user","parts": [{"text": current_prompt}]}
        ]



        response_text = gemini_api.generate_content(
            model=MODEL_NAME,
            contents=contents_payload,
            system_instruction=system_instruction
        )

        st.session_state.rag_response['answer'] = response_text


# Button to trigger the RAG query
st.button("3. Get Grounded Answer", on_click=run_rag_query, type="primary")

#4) Output box for populating response
st.subheader("RAG Response")

if st.session_state.get('rag_response') and st.session_state['rag_response'].get('answer'):

    #Explicitly display the prompt that generated this answer
    st.markdown("---")
    st.markdown(f"**Question Asked: ** *{st.session_state['rag_response']['prompt']}*")
    st.markdown(st.session_state['rag_response']['answer'])
    st.markdown("---")

else:
    st.info("Your answer will appear here after you click 'Get Grounded Naswer.'")

st.markdown("---")

st.caption(
    "Workshop key takeaway: The RAG System works by COnstructing a powerful prompt that includes both the external "
    "context (your document) and the user's query, forcing the LLM to act as a document reader."
)
