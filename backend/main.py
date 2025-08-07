# main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = FastAPI()

# CORS Middleware (allows frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load DialoGPT model & tokenizer
model_name = "microsoft/DialoGPT-medium"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
model.eval()

# Store chat history
chat_history_ids = None


@app.post("/chat")
async def chat(request: Request):
    global chat_history_ids
    data = await request.json()
    prompt = data.get("message", "")

    if not prompt:
        return {"response": "No input received."}

    new_input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors='pt')

    if chat_history_ids is not None:
        # Append the new user input to the chat history
        bot_input_ids = torch.cat([chat_history_ids, new_input_ids], dim=-1)

        # Trim input if too long (to avoid hitting the token limit)
        if bot_input_ids.shape[-1] > 1000:
            bot_input_ids = bot_input_ids[:, -1000:]
    else:
        bot_input_ids = new_input_ids

    # Generate response
    with torch.no_grad():
        chat_history_ids = model.generate(
            bot_input_ids,
            max_length=1000,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.8,
        )

    # Decode only the new reply part
    reply = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
    return {"response": reply}


@app.post("/reset")
def reset_chat():
    global chat_history_ids
    chat_history_ids = None
    return {"status": "Chat history reset."}
