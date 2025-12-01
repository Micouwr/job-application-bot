.PHONY: all clean install test build build-mac build-win package-mac

# Default target
all: build

# Install all dependencies (dev and runtime)
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pyinstaller>=6.0.0

# Clean build artifacts and cache
clean:
	rm -rf build/ dist/
	rm -rf *.spec
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

# Run test suite
test:
	python -m pytest tests/ -v

# --- Primary Build Commands ---

# Build for current platform
build: clean
	@echo "🔨 Building Job Application Bot for $(shell uname -s)..."
	@if [ ! -f "job_application_bot.spec" ]; then \
		echo "❌ job_application_bot.spec not found! Run: python build_standalone.py first"; \
		exit 1; \
	fi
	pyinstaller --clean --noconfirm job_application_bot.spec
	@echo "✅ Build complete in dist/ folder"

# Build for macOS (explicit)
build-mac: clean
	@echo "🔨 Building macOS application bundle..."
	@if [ ! -f "job_application_bot.spec" ]; then \
		echo "❌ job_application_bot.spec not found!"; \
		exit 1; \
	fi
	pyinstaller --clean --noconfirm job_application_bot.spec
	@echo "✅ macOS app bundle: dist/JobApplicationBot.app"

# Build for Windows (run from Windows)
build-win: clean
	@echo "🔨 Building Windows executable..."
	@if not exist "job_application_bot.spec" ( \
		echo ❌ job_application_bot.spec not found! & \
		exit /b 1 \
	)
	pyinstaller --clean --noconfirm job_application_bot.spec
	@echo "✅ Windows executable: dist\JobApplicationBot\JobApplicationBot.exe"

# --- Packaging (macOS only) ---

# Create DMG installer for macOS (requires: brew install create-dmg)
package-mac: build-mac
	@echo "📦 Creating DMG package for macOS..."
	@if ! command -v create-dmg &> /dev/null; then \
		echo "⚠️  create-dmg not found. Install with: brew install create-dmg"; \
		echo "   Skipping DMG creation..."; \
		exit 0; \
	fi
	@create-dmg \
		--volname "Job Application Bot" \
		--window-pos 200 120 \
		--window-size 800 400 \
		--icon-size 100 \
		--icon "JobApplicationBot.app" 200 190 \
		--hide-extension "JobApplicationBot.app" \
		--app-drop-link 600 185 \
		"dist/JobApplicationBot_v2.0.dmg" \
		"dist/JobApplicationBot.app"
	@echo "✅ DMG package created: dist/JobApplicationBot_v2.0.dmg"

# Quick test run
run:
	python gui/tkinter_app.py

# Development install (with pre-commit hooks)
dev-install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pyinstaller>=6.0.0 pre-commit
	pre-commit install
