import os
import io
import asyncio
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from PIL import Image
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# 🚀 IMPORT OUR MASTER KEY MANAGER 🚀
from core.key_manager import key_manager

# Create a folder to store Vector DB chunks locally
VECTOR_DB_DIR = "vector_db"
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

# 🚀 FUTURE PROOFING: Support up to 30 keys in rotation
MAX_KEY_RETRIES = 30


# ==========================================
# 1. PROCESS & STORE PDF IN VECTOR DB
# ==========================================
async def process_and_store_pdf(
    file_bytes: bytes, document_id: str, user_role: str = "learner"
):
    try:
        # Step 1: Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if not text.strip():
            return (
                False,
                "This PDF seems to be an image or scanned document. Text cannot be extracted.",
            )

        # Step 2: Break text into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)

        # 🚀 SMART RETRY LOOP FOR EMBEDDINGS 🚀
        for attempt in range(MAX_KEY_RETRIES):
            try:
                # Get the current active key sequentially
                current_key = key_manager.get_key(user_role)

                # Agar key_manager None return kare matlab sari keys exhaust ho chuki hain
                if not current_key:
                    return False, "All available API keys are currently exhausted."

                print(
                    f"📄 Embedding PDF: Attempt {attempt + 1} with key {current_key[:10]}..."
                )

                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001", google_api_key=current_key
                )

                # Step 4: Save to FAISS Database locally
                vector_store = FAISS.from_texts(chunks, embeddings)
                store_path = os.path.join(VECTOR_DB_DIR, document_id)
                vector_store.save_local(store_path)

                return True, f"Created {len(chunks)} chunks in Vector DB."

            except Exception as e:
                error_msg = str(e)

                # Check specifically for Quota limits to shift silently
                if (
                    "429" in error_msg
                    or "Quota" in error_msg
                    or "ResourceExhausted" in error_msg
                ):
                    print(
                        "❌ Embedding Quota Exhausted! Silently switching to next key..."
                    )
                    key_manager.mark_key_exhausted(user_role)
                    continue  # Try with next key

                # If error is invalid key (400) or something else, don't loop, just fail
                return False, f"Embedding Error: {error_msg}"

        return False, "All API keys exhausted for PDF processing."

    except Exception as e:
        return False, str(e)


# ==========================================
# 2. REAL-TIME CHAT WITH SMART FALLBACK LOOP
# ==========================================
async def stream_chat_response(
    query: str, document_id: str = None, user_role: str = "learner"
):
    # Strictly define AI identity
    instruction = """
    You are DocuMind, a brilliant, helpful, and highly intelligent AI study assistant.
    CRITICAL RULES:
    1. You MUST NEVER mention that you are an AI created by Google, Alphabet, or Gemini.
    2. Give concise, accurate, and structured answers using Markdown formatting.
    """

    # 🚀 SMART FALLBACK LOOP FOR CHAT 🚀
    for attempt in range(MAX_KEY_RETRIES):
        try:
            # 1. Ask manager for ONE active key
            current_key = key_manager.get_key(user_role)

            if not current_key:
                yield "\n\nDocuMind System Error: ⚠️ Daily limit reached! All API keys have exhausted their quota. Please try again tomorrow."
                return

            print(f"💬 Chat: Attempt {attempt + 1} using Key {current_key[:10]}...")

            # Configure API
            genai.configure(api_key=current_key)

            context = ""
            # Search relevant chunks in Vector DB if a PDF was uploaded
            if document_id:
                store_path = os.path.join(VECTOR_DB_DIR, document_id)
                if os.path.exists(store_path):
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/embedding-001", google_api_key=current_key
                    )
                    vector_store = FAISS.load_local(
                        store_path, embeddings, allow_dangerous_deserialization=True
                    )
                    docs = vector_store.similarity_search(query, k=3)
                    context = "\n\n---\n\n".join([doc.page_content for doc in docs])

            final_prompt = query
            if context:
                final_prompt = f"Use the following document chunks to answer the user's question accurately. If the answer is not in the context, rely on your general knowledge but answer nicely.\n\nDocument Context:\n{context}\n\nUser Question: {query}"

            # Generate chat response
            chat_model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-001", system_instruction=instruction
            )
            response = chat_model.generate_content(final_prompt, stream=True)

            # If successful, yield chunks and return (exiting loop)
            for chunk in response:
                if chunk.text:
                    safe_text = chunk.text.replace("Gemini", "DocuMind").replace(
                        "Google", "our development team"
                    )
                    yield safe_text
                    await asyncio.sleep(0.01)  # Small delay for typewriter effect

            return  # Exit function completely on success

        except Exception as e:
            error_msg = str(e)

            # Silently catch Quota limits and shift to the next key
            if (
                "429" in error_msg
                or "Quota" in error_msg
                or "ResourceExhausted" in error_msg
            ):
                print("❌ Chat Quota Exhausted! Silently switching to next key...")
                key_manager.mark_key_exhausted(user_role)
                continue  # Loop again with next key

            # If error is a Bad Request (400 - Invalid API Key), tell user to fix .env
            elif "400" in error_msg or "API_KEY_INVALID" in error_msg:
                yield f"\n\nDocuMind Configuration Error: One of your API keys is invalid. Please check your .env file."
                return

            # For any other random error
            else:
                yield f"\n\nDocuMind System Error: {error_msg}"
                return

    # If loop finishes all retries without returning, it means all keys are dead
    yield "\n\nDocuMind System Error: ⚠️ Daily limit reached! All API keys have exhausted their quota. Please try again tomorrow."


# ==========================================
# 3. VISION (Image Text Extraction) WITH FALLBACK
# ==========================================
async def extract_text_from_image(image_bytes: bytes, user_role: str = "learner"):
    for attempt in range(MAX_KEY_RETRIES):
        try:
            current_key = key_manager.get_key(user_role)
            if not current_key:
                return "Vision Error: ⚠️ All API keys have exhausted their quota."

            print(f"👁 Vision: Attempt {attempt + 1} using Key {current_key[:10]}...")

            genai.configure(api_key=current_key)
            vision_model = genai.GenerativeModel("gemini-1.5-flash-001")
            pil_image = Image.open(io.BytesIO(image_bytes))
            prompt = "Extract all text, math equations, and important information from this image."

            response = vision_model.generate_content([prompt, pil_image])
            return response.text

        except Exception as e:
            error_msg = str(e)
            if (
                "429" in error_msg
                or "Quota" in error_msg
                or "ResourceExhausted" in error_msg
            ):
                print("❌ Vision Quota Exhausted! Silently switching key...")
                key_manager.mark_key_exhausted(user_role)
                continue
            else:
                return f"Vision Error: {error_msg}"

    return "Vision Error: ⚠️ All API keys have exhausted their quota."
