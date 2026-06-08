from datetime import timezone
import os
import glob

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'datetime.now(timezone.utc).replace(tzinfo=None)' not in content:
        return False

    # Replace datetime.now(timezone.utc).replace(tzinfo=None) with datetime.now(timezone.utc).replace(tzinfo=None)
    content = content.replace('datetime.now(timezone.utc).replace(tzinfo=None)', 'datetime.now(timezone.utc).replace(tzinfo=None)')
    
    # Add timezone to the datetime import if not there
    if 'from datetime import ' in content and 'timezone' not in content:
        content = content.replace('from datetime import datetime, timedelta', 'from datetime import datetime, timedelta, timezone')
        content = content.replace('from datetime import datetime\n', 'from datetime import datetime, timezone\n')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return True

def main():
    root_dir = r"c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
    py_files = glob.glob(os.path.join(root_dir, '**', '*.py'), recursive=True)
    count = 0
    for file in py_files:
        if 'venv' in file or '.venv' in file:
            continue
        if fix_file(file):
            print(f"Fixed {file}")
            count += 1
    print(f"Fixed {count} files.")

if __name__ == '__main__':
    main()
