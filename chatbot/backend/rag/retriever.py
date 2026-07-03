import asyncio
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from chatbot.backend.config import CHROMA_PATH, RETRIEVER_K, EMBEDDING_MODEL_NAME, RERANKER_MODEL_NAME, RERANKER_TOP_N, SIMILARITY_WEIGHT

_compression_retriever = None
_lock = asyncio.Lock()

async def get_retriever():
    global _compression_retriever
    async with _lock:
        if _compression_retriever is not None:
            return _compression_retriever
        
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=CHROMA_PATH)
        vector_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": RETRIEVER_K})

        data = vectorstore.get()

        documents = []

        for text, metadata in zip(data["documents"], data["metadatas"]):
            documents.append(Document(page_content=text, metadata=metadata))

        bm25_retriever = BM25Retriever.from_documents(documents, k=RETRIEVER_K)

        retriever = EnsembleRetriever(retrievers=[vector_retriever, bm25_retriever], weights=[SIMILARITY_WEIGHT, 1 - SIMILARITY_WEIGHT])

        cross_encoder = HuggingFaceCrossEncoder(model_name=RERANKER_MODEL_NAME)
        reranker = CrossEncoderReranker(model=cross_encoder, top_n=RERANKER_TOP_N)

        _compression_retriever = ContextualCompressionRetriever(
            base_compressor=reranker,
            base_retriever=retriever
        )
    
    return _compression_retriever