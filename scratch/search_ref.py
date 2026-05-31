# scratch/search_ref.py
with open(".reference/llm-upload-post.md", "r", encoding="utf-8") as f:
    content = f.read()

# Let's find any occurrences of "POST /api/upload " or similar general upload
pos = content.find("POST /api/upload\n")
if pos == -1:
    pos = content.find("POST /api/upload ")
if pos == -1:
    pos = content.find("POST /api/upload\\")
if pos == -1:
    pos = content.find("/api/upload")

if pos != -1:
    print("Found upload section:")
    print(content[pos-100:pos+1500])
else:
    print("Upload section not found")
