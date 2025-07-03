# Install required libraries
!pip install transformers torch

# 1) Imports
from transformers import AutoTokenizer, AutoModel
import torch
import json

# 2) Specify model name
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"

# 3) Load tokenizer & model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model     = AutoModel.from_pretrained(MODEL_NAME)

# 4) Your sample documents (replace with your Hospital XYZ notes)
documents = [
    "The patient shows signs of myocardial infarction.",
    "Evidence of chronic obstructive pulmonary disease (COPD).",
    "History of type 2 diabetes mellitus.",
    "MRI indicates presence of a small ischemic stroke."
]

# 5) Prepare a list to hold text + embedding pairs
embeddings_data = []

# 6) Loop through each document and compute its embedding
for doc in documents:
    # a) Tokenize text → input IDs + attention mask
    inputs = tokenizer(
        doc, 
        return_tensors="pt",   # PyTorch tensors
        padding=True,          # pad to longest in batch (here single)
        truncation=True        # truncate if too long
    )
    
    # b) Forward-pass through model (no gradient needed)
    with torch.no_grad():
        outputs = model(**inputs)
    
    # c) Extract the [CLS] token embedding as sentence vector
    #    outputs.last_hidden_state shape: [batch, seq_len, hidden_size]
    #    we take index 0 of seq_len (the [CLS] token)
    cls_emb = outputs.last_hidden_state[0, 0, :]

    # d) Convert to plain Python list for JSON serialization
    emb_list = cls_emb.tolist()
    
    # e) Append a dict with the original text and its vector
    embeddings_data.append({
        "text":      doc,
        "embedding": emb_list
    })

# 7) Write out the entire list to JSON
with open("embeddings.json", "w") as f:
    json.dump(embeddings_data, f)

print(f"Saved {len(embeddings_data)} embeddings to embeddings.json")
