import os
import glob

def fix_imports(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'timezone' in content and 'from datetime import timezone' not in content and 'import timezone' not in content:
        # Just prepend it
        content = 'from datetime import timezone\n' + content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    root_dir = r"c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
    py_files = glob.glob(os.path.join(root_dir, '**', '*.py'), recursive=True)
    count = 0
    for file in py_files:
        if 'venv' in file or '.venv' in file:
            continue
        if fix_imports(file):
            print(f"Fixed imports in {file}")
            count += 1
    print(f"Fixed {count} files.")

if __name__ == '__main__':
    main()
