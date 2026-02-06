# https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2

# pip install transformers>=4.47.1
# pip install torch>=2.0.0

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

model_name = "nvidia/llama-nemotron-rerank-1b-v2"
device = "cuda:0" if torch.cuda.is_available() else "cpu"
max_length = 512

tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True,
    padding_side="left",
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
).eval()

if model.config.pad_token_id is None:
    model.config.pad_token_id = tokenizer.eos_token_id

model = model.to(device)


def prompt_template(query: str, passage: str) -> str:
    return f"question:{query} \n \n passage:{passage}"


# Example usage
query = "how much protein should a female eat?"
documents = [
    "As a general guideline, the CDC's average requirement of protein for women ages 19 to 70 is 46 grams per day. But, as you can see from this chart, you'll need to increase that if you're expecting or training for a marathon. Check out the chart below to see how much protein you should be eating each day.",
    "Definition of summit for English Language Learners. : 1 the highest point of a mountain : the top of a mountain. : 2 the highest level. : 3 a meeting or series of meetings between the leaders of two or more governments.",
    "Calorie needs and nutrient balance can vary based on age, activity level, and health status. While general guidelines exist, individual requirements may differ. Consult a healthcare provider for personalized nutrition advice.",
]

texts = [prompt_template(query, doc) for doc in documents]

batch_dict = tokenizer(
    texts,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=max_length,
)

batch_dict = {k: v.to(device) for k, v in batch_dict.items()}

with torch.inference_mode():
    logits = model(**batch_dict).logits
    scores = logits.view(-1).cpu().tolist()

print("Query:", query)
print("\nRanked documents:")
for idx in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True):
    print(f"  Score: {scores[idx]:.4f} - {documents[idx][:80]}...")
