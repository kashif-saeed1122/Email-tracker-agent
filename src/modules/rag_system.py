import voyageai
import chromadb
from typing import Dict, Optional
import uuid


class RAGSystem:
    """RAG system for semantic search over bills"""
    
    def __init__(
        self,
        voyage_api_key: str,
        chroma_path: str = "./data/vector_store/",
        collection_name: str = "bills"
    ):
        """
        Initialize RAG system
        
        Args:
            voyage_api_key: Voyage AI API key
            chroma_path: Path to ChromaDB storage
            collection_name: ChromaDB collection name
        """
        self.voyage_client = voyageai.Client(api_key=voyage_api_key)
        self.embedding_model = "voyage-2"
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def add_document(
        self,
        text: str,
        metadata: Dict,
        doc_id: Optional[str] = None
    ) -> Dict:
        """
        Add a document to the vector store
        
        Args:
            text: Document text content
            metadata: Document metadata (vendor, amount, dates, etc.)
            doc_id: Optional document ID
            
        Returns:
            Dict with result and document_id
        """
        try:
            # Generate ID if not provided
            if not doc_id:
                doc_id = str(uuid.uuid4())
            
            # Generate embedding using Voyage AI
            embedding = self.voyage_client.embed(
                texts=[text],
                model=self.embedding_model
            ).embeddings[0]
            
            # Add to ChromaDB
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
            
            return {
                "success": True,
                "document_id": doc_id,
                "message": "Document added successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        top_k: int = 5
    ) -> Dict:
        """
        Semantic search over documents
        
        Args:
            query: Natural language search query
            filters: Optional metadata filters
            top_k: Number of results to return
            
        Returns:
            Dict with search results and relevance scores
        """
        try:
            # Generate query embedding
            query_embedding = self.voyage_client.embed(
                texts=[query],
                model=self.embedding_model
            ).embeddings[0]
            
            # Build where clause for filtering
            where = None
            if filters:
                where = {}
                if 'category' in filters:
                    where['category'] = filters['category']
                if 'vendor' in filters:
                    where['vendor'] = {'$contains': filters['vendor']}
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where if where else None
            )
            
            # Format results
            formatted_results = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'relevance_score': 1 - results['distances'][0][i] if results['distances'] else 1.0
                    })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def delete_document(self, doc_id: str) -> Dict:
        """
        Delete a document from the vector store
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dict with success status
        """
        try:
            self.collection.delete(ids=[doc_id])
            
            return {
                "success": True,
                "message": f"Document {doc_id} deleted"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection
        
        Returns:
            Dict with collection stats
        """
        try:
            count = self.collection.count()
            
            return {
                "success": True,
                "collection_name": self.collection.name,
                "document_count": count,
                "embedding_model": self.embedding_model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_document(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Update an existing document
        
        Args:
            doc_id: Document ID
            text: New text content (optional)
            metadata: New metadata (optional)
            
        Returns:
            Dict with success status
        """
        try:
            update_params = {"ids": [doc_id]}
            
            if text:
                # Generate new embedding
                embedding = self.voyage_client.embed(
                    texts=[text],
                    model=self.embedding_model
                ).embeddings[0]
                
                update_params["embeddings"] = [embedding]
                update_params["documents"] = [text]
            
            if metadata:
                update_params["metadatas"] = [metadata]
            
            self.collection.update(**update_params)
            
            return {
                "success": True,
                "message": f"Document {doc_id} updated"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }