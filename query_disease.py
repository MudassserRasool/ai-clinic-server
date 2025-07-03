# Install required libraries
# !pip install transformers torch scikit-learn

# 1) Imports
from transformers import AutoTokenizer, AutoModel
import torch
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 2) Load saved embeddings from JSON
with open("embeddings.json", "r") as f:
    data = json.load(f)

# 3) Split into a list of texts and a NumPy array of embeddings
texts = [ entry["text"]      for entry in data ]
embs  = np.array([ entry["embedding"] for entry in data ])

# 4) Reload the same BioClinicalBERT model & tokenizer
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
tokenizer  = AutoTokenizer.from_pretrained(MODEL_NAME)
model      = AutoModel.from_pretrained(MODEL_NAME)

def embed_text(text: str) -> np.ndarray:
    """
    Given a piece of text, return its BioClinicalBERT [CLS] embedding as a NumPy array.
    """
    # Tokenize and convert to tensors
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        padding=True, 
        truncation=True
    )
    # Forward pass without gradient tracking
    with torch.no_grad():
        outputs = model(**inputs)
    # Extract [CLS] token (first token) embedding
    cls_emb = outputs.last_hidden_state[0, 0, :]
    # Convert to NumPy
    return cls_emb.cpu().numpy()

# 5) Prompt the user for a clinical query
query = input("Enter your clinical query: ").strip()

# 6) Embed the query
q_emb = embed_text(query)

# 7) Compute cosine similarities between query and each document
#    cosine_similarity expects 2D arrays: (n_samples, n_features)
sims = cosine_similarity(q_emb.reshape(1, -1), embs)[0]

# 8) Identify the index of the best match
best_idx = sims.argmax()
best_score = sims[best_idx]
best_text  = texts[best_idx]

# 9) Print out the “reply”
print("\n🔍 Best match found:")
print(f"Text  : {best_text}")
print(f"Score : {best_score:.4f}")
