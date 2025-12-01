from PyInstaller.utils.hooks import collect_hidden_imports

# This hook file explicitly tells PyInstaller about hidden dependencies
# that its static analysis might miss.

# --- PyPDF2 ---
# The _crypter module is often missed.
hiddenimports = ['PyPDF2._crypter']

# --- Tiktoken ---
# This package uses dynamic imports that PyInstaller cannot see.
hiddenimports += collect_hidden_imports('tiktoken_ext')

# --- Jinja2 ---
# Jinja2 also uses dynamic imports for its extensions.
hiddenimports += collect_hidden_imports('jinja2.ext')

# --- BeautifulSoup4 ---
# Sometimes needs to be explicitly included.
hiddenimports += collect_hidden_imports('beautifulsoup4')
