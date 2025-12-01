# test_paths.py
import sys
from pathlib import Path
from utils.paths import get_base_path, get_user_data_path

def main():
    print(f"--- Path Verification Script ---")
    print(f"Platform: {sys.platform}")

    base_path = get_base_path()
    user_data_path = get_user_data_path()

    print(f"Base Path (get_base_path): {base_path}")
    print(f"User Data Path (get_user_data_path): {user_data_path}")

    # Simulate directory creation from config/settings.py
    print("\nSimulating directory creation...")
    try:
        user_data_path.mkdir(parents=True, exist_ok=True)
        (user_data_path / "data").mkdir(exist_ok=True)
        (user_data_path / "logs").mkdir(exist_ok=True)
        print("✅ Successfully created user data directories (simulation).")
    except Exception as e:
        print(f"❌ Failed to create directories: {e}")

if __name__ == "__main__":
    main()
