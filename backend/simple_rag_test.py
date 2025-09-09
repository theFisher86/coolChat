#!/usr/bin/env python3
"""Simple RAG Testing Script - No relative imports"""

import os
import sys
import asyncio

def configure_path():
    """Configure Python path for imports"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    return current_dir

def test_credentials_simple():
    """Simple credential test without complex imports"""
    print("🔍 Testing RAG Credentials...")

    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()

        # Test basic config
        provider = os.getenv("RAG_PROVIDER", "ollama")
        print(f"📊 Provider: {provider}")

        if provider == "ollama":
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "nomic-embed-text:latest")
            print(f"🦙 Ollama URL: {ollama_url}")
            print(f"🤖 Model: {ollama_model}")

            # Test connectivity
            import httpx
            try:
                response = httpx.get(f"{ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if ollama_model in model_names:
                        print(f"✅ Ollama working - Model '{ollama_model}' is available")
                        return True
                    else:
                        print(f"⚠️ Ollama working but model '{ollama_model}' not found. Available: {model_names}")
                        return False
                else:
                    print("❌ Ollama API not responding")
                    return False
            except Exception as e:
                print(f"❌ Cannot connect to Ollama: {e}")
                print("💡 Make sure Ollama is running: ollama serve")
                return False

        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                print(f"🔑 Gemini API Key: {api_key[:10]}...")
                print("✅ Gemini credentials configured")
                return True
            else:
                print("❌ Gemini API key not found")
                return False

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install required packages: pip install python-dotenv httpx")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_full_rag():
    """Test full RAG system"""
    print("🔍 Testing Full RAG System...")

        # This would require the full application context
    print("⚠️ Full RAG test requires application context")
    print("💡 Run through FastAPI instead: python main.py then test via API")
    return False

def main():
    """Main test function"""
    print("🤖 CoolChat RAG Simple Tester")
    print("=" * 40)

    configure_path()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python simple_rag_test.py credentials")
        print("  python simple_rag_test.py full")
        return

    command = sys.argv[1]

    if command == "credentials":
        success = test_credentials_simple()
        if success:
            print("\n✅ Credentials test passed!")
            print("🎯 Next: Generate embeddings for your lore entries")
        else:
            print("\n❌ Credentials test failed")
            print("🔧 Check your .env file configuration")
    elif command == "full":
        asyncio.run(test_full_rag())
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()