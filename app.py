import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("Missing API Key! Please set GOOGLE_API_KEY in your .env file.")
    st.stop()

genai.configure(api_key=api_key)


def get_pdf_text(pdf_docs):
    """Extract text from uploaded PDFs."""
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        except Exception as e:
            st.error(f"Error processing {pdf.name}: {str(e)}")
    return text.strip()


def get_text_chunks(text):
    """Split text into smaller chunks for vector storage."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)


def get_vector_store(text_chunks):
    """Convert text chunks into embeddings and store them in FAISS."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")


def get_conversational_chain(vectorstore):
    """Set up retrieval-based QA chain using RetrievalQA."""
    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0.3)  # Updated model name
    return RetrievalQA.from_chain_type(
        llm=model,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        return_source_documents=True  # Optional: Include source documents in the response
    )


def user_input(user_question):
    """Handle user questions and fetch relevant answers."""
    if not os.path.exists("faiss_index"):
        st.error("No PDF data found. Please upload and process PDFs first.")
        return

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

    chain = get_conversational_chain(vectorstore)

    # ✅ Pass the question as a string
    response = chain.invoke(user_question)  # Correct input format

    st.write("**Reply:**", response["result"])  # Extract the answer from the response


def main():
    """Main function for Streamlit UI."""
    st.set_page_config(page_title="Chat with PDFs")
    st.header("Chat with PDF using Gemini 💁")

    user_question = st.text_input("Ask a question from the PDFs")

    if user_question:
        try:
            user_input(user_question)
        except Exception as e:
            st.error(f"Error processing your question: {str(e)}")

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDFs and click Submit & Process", accept_multiple_files=True)

        if st.button("Submit & Process"):
            if pdf_docs:
                with st.spinner("Processing..."):
                    try:
                        raw_text = get_pdf_text(pdf_docs)
                        if raw_text:
                            text_chunks = get_text_chunks(raw_text)
                            get_vector_store(text_chunks)
                            st.success("Processing completed! You can now ask questions.")
                        else:
                            st.warning("No readable text found in the PDFs.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please upload at least one PDF file.")


if __name__ == "__main__":
    main()