import os
import glob

def fix_tzinfo(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace datetime.now(timezone.utc).replace(tzinfo=None) with datetime.now(timezone.utc).replace(tzinfo=None)
    # BUT only if not already having .replace
    if 'datetime.now(timezone.utc).replace(tzinfo=None)' in content:
        content = content.replace('datetime.now(timezone.utc).replace(tzinfo=None)', 'datetime.now(timezone.utc).replace(tzinfo=None)')
        content = content.replace('.replace(tzinfo=None)', '.replace(tzinfo=None)')
        content = content.replace('.replace(hour=0', '.replace(hour=0')
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
        if fix_tzinfo(file):
            print(f"Fixed tzinfo in {file}")
            count += 1
    print(f"Fixed {count} files.")

if __name__ == '__main__':
    main()
