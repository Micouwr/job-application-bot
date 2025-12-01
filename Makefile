.PHONY: all clean install test build build-mac build-win package-mac

# Default command
all: build

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pyinstaller

# Clean build artifacts
clean:
	rm -rf build/ dist/
	rm -rf *.spec
	find . -type d -name "__pycache__" -exec rm -r {} +

# Run tests
test:
	python -m pytest tests/

# --- Build Commands ---

# Generic build (defaults to mac)
build: build-mac

# Build the macOS application bundle
build-mac:
	@echo "Building macOS application..."
	pyinstaller --clean --noconfirm JobApplicationBot.spec
	@echo "macOS build complete in dist/ folder."

# Build the Windows executable
build-win:
	@echo "Building Windows executable..."
	pyinstaller --clean --noconfirm JobApplicationBot.spec
	@echo "Windows build complete in dist/ folder."

# --- Packaging Commands (macOS Example) ---

# Create a DMG for macOS distribution (requires create-dmg)
package-mac: build-mac
	@echo "Creating DMG package for macOS..."
	@if ! command -v create-dmg &> /dev/null; then \
		echo "Warning: create-dmg command not found. Skipping DMG creation."; \
		echo "Install with: brew install create-dmg"; \
		exit 0; \
	fi
	create-dmg \
		--volname "Job Application Bot" \
		--window-pos 200 120 \
		--window-size 800 400 \
		--icon-size 100 \
		--icon "JobApplicationBot.app" 200 190 \
		--hide-extension "JobApplicationBot.app" \
		--app-drop-link 600 185 \
		"dist/JobApplicationBot.dmg" \
		"dist/JobApplicationBot.app"
	@echo "DMG package created successfully."
