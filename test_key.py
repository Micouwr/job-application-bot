from config.settings import GEMINI_API_KEY

print("=" * 50)
print("API KEY DEBUG")
print("=" * 50)
print(f"Key loaded: {'YES' if GEMINI_API_KEY else 'NO'}")
if GEMINI_API_KEY:
    print(f"Key prefix: {GEMINI_API_KEY[:15]}...")
    print(f"Key length: {len(GEMINI_API_KEY)} characters")
    print(f"Looks valid: {'AIzaSy' in GEMINI_API_KEY}")
else:
    print("ERROR: No key found!")
print("=" * 50)
