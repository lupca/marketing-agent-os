import os
import re

def refactor_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Cannot read {filepath}: {e}")
        return

    if "SessionLocal" not in content and "get_session" not in content:
        return
        
    original_content = content

    # Replace the import
    content = re.sub(r'from\s+db\.connection\s+import\s+(.*?)\bSessionLocal\b(.*)', 
                     lambda m: f"from db.connection import {m.group(1)}{m.group(2)}".replace("import ,", "import ").replace(", ,", ",").strip().strip(',') + "\nfrom core.dependencies import get_session" if m.group(1).strip() or m.group(2).strip() else "from core.dependencies import get_session", 
                     content)
    # Cleanup empty imports like "from db.connection import"
    content = re.sub(r'from\s+db\.connection\s+import\s*\n', '', content)

    lines = content.split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Match `db = SessionLocal()` or `db: Session = SessionLocal()`
        match = re.search(r'^(\s*)([\w_]+)(?:\s*:\s*[\w_]+)?\s*=\s*SessionLocal\(\)', line)
        if match:
            indent = match.group(1)
            var_name = match.group(2)
            
            new_lines.append(f"{indent}with get_session() as {var_name}:")
            
            i += 1
            # Now we process all subsequent lines that are indented under `indent` or same level.
            # We will indent everything by 4 spaces.
            # When we see a `try:` at the EXACT SAME `indent`, we can strip the `try:` line and just keep the content (optional, but requirement says: "Ensure the code inside the old try...finally: db.close() is properly indented under the with block"). Wait, if we keep `try`, it's harmless. But removing `finally: db.close()` is required.
            
            # A simpler way: we process lines, indenting them if they are at or beyond `indent`,
            # until we hit a line that is LESS indented than `indent` (meaning the block ended)
            # EXCEPTION: if we see `finally:` at exactly `indent`, we skip it and skip the next line if it's `db.close()`.
            
            # Wait, often `try:` is at the same level as `db = SessionLocal()`:
            # db = SessionLocal()
            # try:
            #     ...
            # finally:
            #     db.close()
            #
            # We want:
            # with get_session() as db:
            #     try:
            #         ...
            #     # NO finally block
            
            inside_finally = False
            while i < len(lines):
                sub_line = lines[i]
                
                # Check for block exit
                if sub_line.strip() and not sub_line.startswith(indent):
                    # We reached a line that has less indentation. Block is done.
                    break
                
                # Handle `finally:` block specifically for the current db.close()
                if sub_line.startswith(indent + "finally:") and sub_line.strip() == "finally:":
                    # Next line should be db.close()
                    # Wait, if `finally` is exactly at `indent`? Usually `try` is at same `indent` as `db = SessionLocal()`.
                    # E.g.,
                    #     db = SessionLocal()
                    #     try:
                    #         ...
                    #     finally:
                    #         db.close()
                    # If `finally:` is at `indent`, it means it's a try-finally at the SAME scope.
                    inside_finally = True
                    i += 1
                    continue
                
                if inside_finally:
                    if sub_line.strip() == f"{var_name}.close()":
                        i += 1
                        continue
                    if sub_line.strip() == "" or sub_line.strip() == "pass":
                        i += 1
                        continue
                    # If we found something else in the finally block, we should keep it, but maybe just un-indent?
                    # For safety, let's just turn off inside_finally if indentation changes back to <= indent
                    if sub_line.strip() and not sub_line.startswith(indent + " "):
                        inside_finally = False
                
                # Indent line
                if sub_line.strip():
                    new_lines.append("    " + sub_line)
                else:
                    new_lines.append(sub_line)
                i += 1
            
            continue # Already advanced `i`
            
        new_lines.append(line)
        i += 1
        
    final_content = '\n'.join(new_lines)
    
    # Check if there are still any `db.close()` left
    # final_content = re.sub(r'^\s*db\.close\(\)\s*\n?', '', final_content, flags=re.MULTILINE)
    
    if final_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"Refactored: {filepath}")

# Walk through all Python files
for root, _, files in os.walk('.'):
    if 'test' in root or 'docs' in root or 'scratch' in root or 'migrations' in root or '.chainlit' in root or '__pycache__' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py') and file != 'dependencies.py' and file != 'connection.py':
            refactor_file(os.path.join(root, file))

# Wait, `db/seed.py` might need it too.
