#!/usr/bin/env python3

with open('routers/lore.py', 'r') as f:
    content = f.read()

# Replace the function signature to add use_rag parameter
old_signature = """async def search_lorebooks(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, description="Maximum number of results"),
    db: Session = Depends(get_db)
):"""

new_signature = """async def search_lorebooks(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, description="Maximum number of results"),
    use_rag: bool = Query(False, description="Enable RAG-powered semantic search"),
    db: Session = Depends(get_db)
):"""

new_docstring = """""Search lore entries with advanced keyword matching or RAG-powered search"""

content = content.replace('"""Search lore entries with advanced keyword matching logic"""', new_docstring)
content = content.replace(old_signature, new_signature)

# Write back
with open('routers/lore.py', 'w') as f:
    f.write(content)

print('Updated function signature with use_rag parameter')