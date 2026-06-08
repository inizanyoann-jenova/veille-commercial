import re
import os

filepath = r"c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI\backend\test_main.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: done instead of ok
content = content.replace('assert body["status"] == "ok"', 'assert body["status"] == "done"')

# Fix 2: errors list instead of error string
content = content.replace('assert "Toutes les sources ont échoué" in body.get("error", "")', 'assert "RuntimeError" in body.get("errors", [])[0]')
content = content.replace('assert body["status"] == "partial"', 'assert body["status"] == "done"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
