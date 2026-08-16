from openai import OpenAI
import os
import sys

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
_REASONING_COLOR = "\033[90m" if _USE_COLOR else ""
_RESET_COLOR = "\033[0m" if _USE_COLOR else ""

NAME = "ayush"
EMAIL = "ayush946589454.84@gmail.com"

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.getenv("NVIDIA_API_KEY", "your-api-key-here")
)

print(f"🤖 Personal AI Assistant - {NAME}")
print(f"📧 Contact: {EMAIL}")
print("-" * 40)

completion = client.chat.completions.create(
  model="z-ai/glm-5.2",
  messages=[{"role":"user","content":"Hello, how are you?"}],
  temperature=1,
  top_p=1,
  max_tokens=16384,
  seed=42,
  
  stream=True
)

for chunk in completion:
  if not getattr(chunk, "choices", None):
    continue
  if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
    continue
  delta = chunk.choices[0].delta
  if getattr(delta, "content", None) is not None:
    print(delta.content, end="")

print(f"\n\n---\nSession ended. Have a great day, {NAME}!")