'''Interface definition and common implemetations for vectordb classes'''
import os
from typing import List

import schema

#pylint: disable=too-few-public-methods, unused-argument

class VectordbInterface:
    '''Interface for vector database technology, its connection, configs and operations'''
    db_host: str = None  # Host name to connect to a remote DB deployment
    db_port: str = None # Port to connect to a remote DB deployment
    db_path: str = "../chromadb" # Path for a local DB, if that is being used
    collection_name:str =  "aDotBCollection"  # Collection to connect to a remote/local DB
    db_conn=None
    def __init__(self, host, port, path, collection_name) -> None:
        '''Get a connection ready'''
        return
    def add_to_collection(self, docs: List[schema.Document], **kwargs) -> None:
        '''Add objects in document format to DB'''
        return
