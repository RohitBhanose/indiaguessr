import os

src_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'src'))
print("Searching in:", src_dir)

for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith('.tsx') or f.endswith('.ts'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if 'leaflet' in content.lower():
                        print(f"Found leaflet reference in: {path}")
            except Exception as e:
                print(f"Error reading {path}: {e}")
