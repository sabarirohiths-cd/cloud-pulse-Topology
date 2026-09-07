import ast
import os
import glob

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        classes = []
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) and not isinstance(node.parent if hasattr(node, 'parent') else None, ast.ClassDef):
                # Just getting top-level functions for simplicity, or all functions
                functions.append(node.name)
        return {'classes': classes, 'functions': functions}
    except Exception as e:
        return {'error': str(e)}

backend_dir = 'backend'
for root, dirs, files in os.walk(backend_dir):
    if 'venv' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            res = analyze_file(filepath)
            if 'error' not in res and (res['classes'] or res['functions']):
                print(f"File: {filepath}")
                if res['classes']:
                    print(f"  Classes: {', '.join(res['classes'])}")
                if res['functions']:
                    print(f"  Functions: {', '.join(res['functions'])}")
                print()
