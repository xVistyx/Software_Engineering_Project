
from preprocess import preprocess


def tokenize(query: str, page_data: dict, tokenizer):
    prompt = (
        f"Study session goal: {query}\n",
        f"{preprocess(page_data)}\n\n"
        "Is this page relevant to the study session goal?"
        'Answer with just JSON: {"relevant": true or false, "confidence_score": value between 0 and 1, with 2 decimal place, "reason": "short reason for true or false"}'
    )
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    return 