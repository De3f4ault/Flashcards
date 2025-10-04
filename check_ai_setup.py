# check_ai_setup.py
from app import create_app
from app.config import Config

app = create_app()

print("=== AI Configuration Check ===")
print(f"AI_ENABLED: {Config.AI_ENABLED}")
print(f"AI_PROVIDER: {Config.AI_PROVIDER}")
print(f"GEMINI_API_KEY set: {'Yes' if Config.GEMINI_API_KEY else 'No'}")
print(f"AI_CARD_GENERATION_ENABLED: {Config.AI_CARD_GENERATION_ENABLED}")

print("\n=== Registered Blueprints ===")
for blueprint_name, blueprint in app.blueprints.items():
    print(f"- {blueprint_name}: {blueprint.url_prefix}")
