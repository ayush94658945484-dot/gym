"""VS Code AI Chat Launcher - Personalized for ayush"""
import os
import sys
import subprocess

# Personal info
NAME = "ayush"
EMAIL = "ayush946589454.84@gmail.com"

def check_api_key():
    """Check if NVIDIA API key is set"""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print(f"⚠️  {NAME}, please set your NVIDIA API key first!")
        print("📋 Open VS Code terminal and run:")
        print("   set NVIDIA_API_KEY=your_nvidia_key_here")
        print("   OR on Linux/Mac: export NVIDIA_API_KEY=your_key")
        return False
    return True

def install_dependencies():
    """Install required packages if missing"""
    import importlib
    try:
        import openai
        importlib.import_module('openai')
        return True
    except ImportError:
        print("📦 Installing openai package...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai"], check=True)
        return True

def run_ai_chat():
    """Run the AI chat with personalization"""
    print(f"\n{'='*60}")
    print(f"🤖 Personal AI Assistant - {NAME}")
    print(f"📧 Contact: {EMAIL}")
    print(f"{'='*60}\n")
    
    from openai import OpenAI
    
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY")
    )
    
    print("🔄 Connecting to NVIDIA API...")
    
    completion = client.chat.completions.create(
        model="z-ai/glm-5.2",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        temperature=1,
        top_p=1,
        max_tokens=16384,
        seed=42,
        stream=True
    )
    
    print("💬 AI Response:")
    print("-" * 40)
    
    for chunk in completion:
        if not getattr(chunk, "choices", None):
            continue
        if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None) is not None:
            print(delta.content, end="", flush=True)
    
    print(f"\n\n✅ Session ended. Have a great day, {NAME}!")

def main():
    """Main entry point"""
    print("=" * 60)
    print("VS Code AI Chat Launcher")
    print("=" * 60)
    
    # Check and install dependencies
    install_dependencies()
    
    # Check API key
    if not check_api_key():
        return
    
    # Run AI chat
    run_ai_chat()

if __name__ == "__main__":
    main()