from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen3-4B"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")

def classify(topic, title, description):
    prompt = f"""Study topic: {topic}

Page title: {title}
Page description: {description}

Is this page relevant to studying the topic above? Answer with just JSON: {{"relevant": true or false, "reason": "short reason"}}"""

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=100)
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True)
    return response

# test it
result = classify(
    topic="Mathematical analysis",
    title="Introduction to Limits and Continuity",
    description="A calculus lecture covering epsilon-delta definitions of limits."
)
print(result)