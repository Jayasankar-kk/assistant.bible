'''Implemetations for vectordb interface for chroma'''
import os
from typing import List
from langchain.schema import Document as LangchainDocument
from langchain.schema import BaseRetriever
from core.vectordb import VectordbInterface
from core.embedding.sentence_transformers import SentenceTransformerEmbedding
import schema
from custom_exceptions import ChromaException

import chromadb
from chromadb.config import Settings
#pylint: disable=too-few-public-methods, unused-argument
QUERY_LIMIT = os.getenv('CHROMA_DB_QUERY_LIMIT', "10")

class Chroma(VectordbInterface, BaseRetriever):
    '''Interface for vector database technology, its connection, configs and operations'''
    db_host: str = None  # Host name to connect to a remote DB deployment
    db_port: str = None # Port to connect to a remote DB deployment
    db_path: str = "chromadb_store" # Path for a local DB, if that is being used
    collection_name:str = "aDotBCollection"  # Collection to connect to a remote/local DB
    db_conn=None
    db_client=None
    embedding_function=None
    def __init__(self, host=None, port=None, path="chromadb_store", collection_name=None) -> None: #pylint: disable=super-init-not-called
        '''Instanciate a chroma client'''
        if host:
            self.db_host = host
        if port:
            self.db_port = port
        self.db_path = path
        if collection_name:
            self.collection_name = collection_name
        if(self.db_host is None and self.db_port is None):
            # This method connects to the DB that get stored on the server itself
            # where the app is running
            try:
                chroma_client = chromadb.Client(Settings(
                    chroma_db_impl='duckdb+parquet',
                    persist_directory=path))
            except Exception as exe:
                raise ChromaException("While initializing client: "+str(exe)) from exe
        else:
            # This method requires us to run the chroma DB as a separate service
            # (say in docker-compose).
            # In future this would allow us to keep multiple options for DB connection,
            # letting different users set up and host their own chroma DBs where ever they please
            # and just use the correct host and port.
            # Also need to sort out the following
            # * Let the connection details, host, port and collection name be passed in requests
            # * how authentication for chorma DB access will work in that case
            # * how the connection can be handled like session that is started upon
            #   each user's API request to let each user connect to the DB
            #   that he prefers and has rights for(fastapi's Depends())
            try:
                chroma_client = chromadb.Client(Settings(
                    chroma_api_impl="rest",
                    chroma_server_host=host,
                    chroma_server_http_port=port
                ))
            except Exception as exe:
                raise ChromaException("While initializing client: "+str(exe)) from exe
        try:
            # Check for passed embedding function, or use schema.EmbeddingType.DEFAULT
            if not self.embedding_function:
                embedding_function = SentenceTransformerEmbedding().get_embeddings
            self.db_conn = chroma_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                )
            self.db_client = chroma_client
        except Exception as exe:
            raise ChromaException("While initializing collection: "+str(exe)) from exe

    def add_to_collection(self, docs: List[schema.Document], **kwargs) -> None:
        '''Loads the document object as per chroma DB formats into the collection'''
        metas = []
        for doc in docs:
            meta = {}
            meta.update(doc.metadata)
            meta.update({'label':doc.label,
                         "media": ",".join(doc.media),
                         'links':",".join(doc.links)})
            metas.append(meta)
        if docs[0].embedding is None:
            embeddings = None
        else:
            embeddings=[doc.embedding for doc in docs]
        try:
            self.db_conn.add(
                embeddings=embeddings,
                documents=[doc.text for doc in docs],
                metadatas=metas,
                ids=[doc.docId for doc in docs]
            )
            self.db_client.persist()
        except Exception as exe:
            raise ChromaException("While adding data: "+str(exe)) from exe

    def get_relevant_documents(self, query: str, **kwargs) -> List[LangchainDocument]:
        '''Similarity search on the vector store'''
        results = self.db_conn.query(
            query_texts=[query],
            n_results=QUERY_LIMIT,
            # where={"metadata_field": "is_equal_to_this"},
            # where_document={"$contains":"search_string"}
        )
        return [ LangchainDocument(page_content= doc, metadata={ "source": id_ } )
                                for doc, id_ in zip(results['documents'][0], results['ids'][0])]

    async def aget_relevant_documents(self, query: str, **kwargs) -> List[LangchainDocument]:
        '''Similarity search on the vector store'''
        results = self.db_conn.query(
            query_texts=[query],
            n_results=QUERY_LIMIT,
            # where={"metadata_field": "is_equal_to_this"},
            # where_document={"$contains":"search_string"}
        )
        return [ LangchainDocument(page_content= doc, metadata={ "source": id_ } )
                                for doc, id_ in zip(results['documents'][0], results['ids'][0])]

    def get_available_labels(self) -> List[str]:
        '''Query DB and find out the list of labels available in metadata,
        to be used for later filtering'''
        rows = self.db_conn.get( include=["metadatas"])
        labels = [meta['label'] for meta in rows['metadatas']]
        labels = list(set(labels))
        return labels

    def __del__(self):
        '''To persist DB upon app close'''
        self.db_client.persist()
