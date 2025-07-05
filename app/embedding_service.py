try:
    import torch
except ImportError:
    torch = None

import numpy as np
try:
    from transformers import AutoTokenizer, AutoModel
except ImportError:
    AutoTokenizer = None
    AutoModel = None

from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # self.model_name = "biobert-sentence-transformers" # "emilyalsentzer/Bio_ClinicalBERT"
        # self.model_name = "stanford-crfm/BioMedLM"
        self.model_name = "microsoft/BiomedVLP-CXR-BERT-general"
        # self.model_name = "microsoft/BioGPT"

        self.tokenizer = None
        self.model = None
        
        # Initialize device with proper error handling
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        except AttributeError as e:
            logger.error(f"PyTorch installation issue: {e}")
            logger.error("Please reinstall PyTorch: pip install torch")
            # Fallback to CPU string
            self.device = "cpu"
        except Exception as e:
            logger.error(f"Unexpected error initializing device: {e}")
            self.device = "cpu"
        
    async def initialize(self):
        """Initialize the Bio_ClinicalBERT model and tokenizer"""
        if AutoTokenizer is None or AutoModel is None:
            logger.error("Transformers library not available. Please install: pip install transformers")
            raise ImportError("Transformers library is required but not installed")
        
        try:
            logger.info(f"Loading Bio_ClinicalBERT model on {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            logger.info("Bio_ClinicalBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Bio_ClinicalBERT model: {e}")
            raise e
    

    #  create a function that takes in a visit_data and patient_data and returns a string that is the clinical text with demographics AND based on his clinical training tell what medican need to use
    # def suggest_medication(self, patient_data: str) -> str:
    #     # clinical_summary = self.generate_clinical_summary(visit_data, patient_data)

    #     # Tokenize & generate
    #     inputs = self.tokenizer(patient_data, return_tensors="pt", truncation=True).to(self.device)
    #     with torch.no_grad():
    #         outputs = self.model.generate(**inputs, max_length=256, do_sample=True, temperature=0.7)

    #     # Decode result
    #     answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    #     return answer[len(patient_data):].strip()
    


    def create_clinical_text_with_demographics(self, visit_data: Dict, patient_data: Dict = None) -> str:
        """
        Combine clinical data with patient demographics for embedding generation
        Args:
            visit_data: Dictionary containing clinical information
            patient_data: Dictionary containing patient demographics (age, gender)
        Returns:
            Combined clinical text string with demographics
        """
        text_parts = []

        
        
        # Add patient demographics (age group is important for medical similarity)
        if patient_data:
            if patient_data.get("age"):
                age = patient_data["age"]
                # Convert age to age group for better matching
                if age < 18:
                    age_group = "pediatric"
                elif age < 65:
                    age_group = "adult"
                else:
                    age_group = "elderly"
                text_parts.append(f"Age group: {age_group}")
            
            if patient_data.get("gender"):
                text_parts.append(f"Gender: {patient_data['gender']}; ")
        
        # Add the clinical text (without medications)
        clinical_text = self.create_clinical_text(visit_data)
        if clinical_text:
            text_parts.append(clinical_text)
        
        return ". ".join(filter(None, text_parts))
    
    def create_clinical_text(self, visit_data: Dict) -> str:
        """
        Combine clinical data into a single text string for embedding generation
        IMPORTANT: Excludes prescribed medications to focus on medical conditions and symptoms
        Args:
            visit_data: Dictionary containing clinical information
        Returns:
            Combined clinical text string focused on symptoms and conditions
        """
        text_parts = []
                #  for gender, age, weight, height, blood pressure, oxygen level, and other vitals
        if "gender" in visit_data:
            text_parts.append(f"Gender: {visit_data['gender']}; ")
        if "age" in visit_data:
            text_parts.append(f"Age: {visit_data['age']}; ")
       
        
        # Add vitals information (important for medical condition matching)
        if "vitals" in visit_data:
            vitals = visit_data["vitals"]
            text_parts.append(f"Blood pressure: {vitals.get('bloodPressure', '')}; ")
            text_parts.append(f"Oxygen level: {vitals.get('oxygen', '')}; ")
            text_parts.append(f"Weight: {vitals.get('weight', '')}; ")
        
        # Add clinical observations (symptoms and test results)
        if visit_data.get("clinicalTests"):
            text_parts.append(f"Clinical tests: {visit_data['clinicalTests']}; ")
        
        if visit_data.get("doctorNoticed"):
            text_parts.append(f"Doctor observations: {visit_data['doctorNoticed']}; ")
        
        # REMOVED: Prescribed medications - we want to find similar conditions, not similar treatments
        # This allows doctors to see how different cases with similar symptoms were treated
        
        # Recovery status (indicates severity and outcome)
        if "vitals" in visit_data and "didRecover" in visit_data["vitals"]:
            recovery_status = "recovered" if visit_data["vitals"]["didRecover"] else "in treatment"
            text_parts.append(f"Patient status: {recovery_status}; ")
        
        return ". ".join(filter(None, text_parts))
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a given text using Bio_ClinicalBERT
        Args:
            text: Clinical text to embed
        Returns:
            List of floats representing the embedding vector
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        try:
            # Tokenize the text
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # Move inputs to the same device as model
            if isinstance(self.device, str):
                # Fallback case where device is a string
                if self.device == "cuda" and torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                # else keep on CPU (default)
            else:
                # Normal case where device is a torch.device object
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Extract [CLS] token embedding (first token)
            cls_embedding = outputs.last_hidden_state[0, 0, :]
            
            # Convert to CPU and then to list
            embedding_list = cls_embedding.cpu().numpy().tolist()
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise e
    
    def generate_visit_embedding(self, visit_data: Dict) -> List[float]:
        """
        Generate embedding for a complete visit record
        Args:
            visit_data: Visit data dictionary
        Returns:
            Embedding vector as list of floats
        """
        clinical_text = self.create_clinical_text(visit_data)
        # create_clinical_text_with_demographics 
        demographics_text = self.create_clinical_text_with_demographics(visit_data)
        # combine the two texts
        # combined_text = f"{clinical_text} {demographics_text}"
        combined_text = (
           f"Age and other patient information: {demographics_text}. "
           f"Patient characteristics include: {demographics_text}. "
           f"{clinical_text}"
        )

        logger.info(f"Generating embedding for clinical text: {combined_text[:1000]}...")
        return self.embed_text(combined_text)
    
    def find_similar_visits(self, query_embedding: List[float], stored_embeddings: List[Dict], 
                          top_k: int = 5, min_similarity: float = 0.1) -> List[Tuple[Dict, float]]:
        """
        Find similar visits based on embedding similarity
        Args:
            query_embedding: Query embedding vector
            stored_embeddings: List of stored visit embeddings with metadata
            top_k: Number of top similar results to return
            min_similarity: Minimum similarity threshold
        Returns:
            List of tuples containing (visit_data, similarity_score)
        """
        if not stored_embeddings:
            return []
        
        try:
            # Convert to numpy arrays
            query_vector = np.array(query_embedding).reshape(1, -1)
            stored_vectors = np.array([emb["embedding"] for emb in stored_embeddings])
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, stored_vectors)[0]
            
            # Create list of (visit_data, similarity_score) tuples
            results = []
            for i, similarity in enumerate(similarities):
                if similarity >= min_similarity:
                    results.append((stored_embeddings[i], float(similarity)))
            
            # Sort by similarity score (descending) and return top_k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar visits: {e}")
            return []
    
    def query_similar_cases(self, query_text: str, stored_embeddings: List[Dict], 
                          top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Query similar cases using natural language text
        Args:
            query_text: Natural language query about clinical case
            stored_embeddings: List of stored visit embeddings
            top_k: Number of results to return
        Returns:
            List of similar cases with similarity scores
        """
        try:
            # Generate embedding for the query text
            logger.info(f"......Generating embedding for query text: {query_text[:10000]}...")
            query_embedding = self.embed_text(query_text)
            
            # Find similar visits
            return self.find_similar_visits(query_embedding, stored_embeddings, top_k)
            
        except Exception as e:
            logger.error(f"Error querying similar cases: {e}")
            return []

# Global embedding service instance
embedding_service = EmbeddingService() 