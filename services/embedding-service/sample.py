# https://huggingface.co/nvidia/llama-embed-nemotron-8b#usage

# pip install transformers==4.51.0
# pip install flash-attn==2.6.3

# pip install sentence-transformers

from sentence_transformers import SentenceTransformer

attn_implementation = "eager"  # Or "flash_attention_2"
model = SentenceTransformer(
    "nvidia/llama-embed-nemotron-8b",
    trust_remote_code=True,
    model_kwargs={"attn_implementation": attn_implementation, "torch_dtype": "bfloat16"},
    tokenizer_kwargs={"padding_side": "left"},
)

queries = [
    "How do neural networks learn patterns from examples?"
]
documents = [
    "Deep learning models adjust their weights through backpropagation, using gradient descent to minimize error on training data and improve predictions over time.",
    "Market prices are determined by the relationship between how much people want to buy a product and how much is available for sale, with scarcity driving prices up and abundance driving them down.",
]

# NOTE: encode_query uses the "query" prompt automatically
query_embeddings = model.encode_query(queries)
document_embeddings = model.encode_document(documents)

scores = (query_embeddings @ document_embeddings.T)

print(scores.tolist())
# [[0.3770667314529419, 0.05808388814330101]]
