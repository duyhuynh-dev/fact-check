#!/bin/bash
# Script to load evidence documents into the RAG store

API_BASE="http://localhost:8000"
EVIDENCE_DIR="data/evidence"

echo "Loading evidence documents into RAG store..."

for file in "$EVIDENCE_DIR"/*.txt; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        source_name=$(basename "$file" .txt | tr '_' ' ' | sed 's/\b\(.\)/\u\1/g')
        
        echo "Loading: $filename as '$source_name'"
        
        curl -X POST "$API_BASE/v1/evidence/load" \
            -F "file=@$file" \
            -F "source_name=$source_name" \
            -s | python3 -m json.tool
        
        echo ""
    fi
done

echo "✅ Evidence loading complete!"
echo ""
echo "Evidence sources now include:"
echo "  - Holocaust facts"
echo "  - Antisemitic tropes"
echo "  - Conspiracy theories debunked"
echo "  - Israel/Palestine history"
echo "  - Zionism facts"
echo "  - Legitimate Jewish sources ✨ NEW"

