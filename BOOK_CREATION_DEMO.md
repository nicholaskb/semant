# 📚 Children's Book Creation Demo Guide

**Complete walkthrough for generating a children's book**

---

## 🎯 Quick Demo (5 Minutes)

### Step 1: Prerequisites Check

```bash
# 1. Check Python version
python --version
# Should be: Python 3.11+

# 2. Check if Qdrant is running (for image embeddings)
curl http://localhost:6333/health
# Should return: {"status":"ok"}

# 3. Check environment variables
echo $GCS_BUCKET_NAME
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### Step 2: Run the Book Generator

```bash
# Basic command (uses defaults)
python scripts/generate_childrens_book.py \
  --bucket bahroo_public \
  --input-prefix input_kids_monster/ \
  --output-prefix generated_images/

# With custom settings
python scripts/generate_childrens_book.py \
  --bucket bahroo_public \
  --input-prefix input_kids_monster/ \
  --output-prefix generated_images/ \
  --extensions png jpg \
  --max-downloads 5
```

---

## 📋 What Happens During Generation

### Phase 1: Image Ingestion (1-2 min)
- Downloads input images from GCS bucket
- Downloads output images from GCS bucket
- Generates embeddings for all images
- Stores in Qdrant vector database

**Output**: 
```
✅ Images ingested: 15 input, 45 output
```

### Phase 2: Image Pairing (30 sec)
- Finds best matches between input and output images
- Uses semantic similarity (embeddings)
- Creates input→output pairs

**Output**:
```
✅ Pairs created: 12
```

### Phase 3: Page Design (1-2 min)
- Arranges images by color/spatial relationships
- Creates 3x3 or 3x4 grids for each page
- Designs page layouts

**Output**:
```
✅ Pages designed: 6
```

### Phase 4: Story Generation (1-2 min)
- Generates story text for each page
- Uses AI to create age-appropriate content
- Matches text to images

**Output**:
```
✅ Story generated: 6 pages
```

### Phase 5: Book Assembly (30 sec)
- Creates HTML book file
- Combines images and text
- Generates final output

**Output**:
```
✅ HTML Generated: childrens_books/book_20250113_120000.html
```

---

## 📍 Where to Find Your Book

### Output Location
```
generated_books/
└── childrens_book_[timestamp]/
    ├── book.html          ← Open this in browser!
    ├── book.md            ← Markdown version
    └── metadata.json      ← Generation details
```

### Quick Access
```bash
# Find latest book
ls -t generated_books/*/book.html | head -1

# Open in browser (Mac)
open $(ls -t generated_books/*/book.html | head -1)

# Open in browser (Linux)
xdg-open $(ls -t generated_books/*/book.html | head -1)
```

---

## 🎨 Example: Existing Generated Books

### Book 1: "Quacky McWaddles' Big Adventure"
**Location**: `quacky_book_output/quacky_20250922_142953/`

**Preview**:
```markdown
# Quacky McWaddles' Big Adventure

## Page 1: Meet Quacky
Down by the sparkly pond lived a little yellow duckling 
named Quacky McWaddles. He had the BIGGEST orange feet!

## Page 2: Super Splash
Watch me do my SUPER SPLASH! *KER-SPLASH!* 
Oopsie, that was more of a belly-flop!

## Page 3: Too Big Feet
Holy mackerel! My feet are ENORMOUS! 
The other ducklings giggled when he tripped.
```

**View it**:
```bash
cat quacky_book_output/quacky_20250922_142953/quacky_book.md
```

---

## 🔧 Command Options

### Required Arguments
- `--bucket`: GCS bucket name (e.g., `bahroo_public`)

### Optional Arguments
- `--input-prefix`: Input images prefix (default: `input_kids_monster/`)
- `--output-prefix`: Output images prefix (default: `generated_images/`)
- `--extensions`: File extensions to process (e.g., `png jpg`)
- `--overwrite`: Overwrite existing files
- `--max-downloads`: Max concurrent downloads (default: 8)

### Example Commands

**Minimal**:
```bash
python scripts/generate_childrens_book.py --bucket bahroo_public
```

**Full Options**:
```bash
python scripts/generate_childrens_book.py \
  --bucket bahroo_public \
  --input-prefix input_kids_monster/ \
  --output-prefix generated_images/ \
  --extensions png jpg \
  --max-downloads 5 \
  --overwrite
```

---

## 📊 Expected Output

### Console Output
```
╭─────────────────────────────────────────╮
│     Book Generation Summary             │
├─────────────────────────────────────────┤
│ Images Ingested    │ 15                 │
│ Pairs Created      │ 12                  │
│ Pages Designed     │ 6                   │
│ HTML Generated     │ book_20250113.html  │
╰─────────────────────────────────────────╯

✅ Opening book: generated_books/book_20250113_120000.html
```

### Generated Files
```
generated_books/
└── childrens_book_20250113_120000/
    ├── book.html          ← Interactive HTML book
    ├── book.md            ← Markdown version
    ├── metadata.json      ← Generation metadata
    └── images/            ← Local image cache
        ├── input_001.png
        ├── output_001.png
        └── ...
```

---

## 🎬 Live Demo Script

### For Investor Presentation

```bash
# 1. Show existing generated book
echo "📚 Showing existing generated book:"
cat quacky_book_output/quacky_20250922_142953/quacky_book.md | head -20

# 2. Explain the process
echo ""
echo "🎨 This book was generated using:"
echo "   - 12 input images (kids' drawings)"
echo "   - 36 output images (AI-generated)"
echo "   - Multi-agent workflow"
echo "   - Knowledge Graph integration"

# 3. Show how to generate a new one
echo ""
echo "🚀 To generate a new book:"
echo "   python scripts/generate_childrens_book.py \\"
echo "     --bucket bahroo_public \\"
echo "     --input-prefix input_kids_monster/ \\"
echo "     --output-prefix generated_images/"

# 4. Show the HTML output
echo ""
echo "📄 Generated HTML book opens automatically in browser"
```

---

## 🐛 Troubleshooting

### Issue: "Qdrant connection failed"
**Solution**:
```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant:latest

# Verify it's running
curl http://localhost:6333/health
```

### Issue: "GCS bucket not found"
**Solution**:
```bash
# Check bucket name
echo $GCS_BUCKET_NAME

# Or specify in command
python scripts/generate_childrens_book.py --bucket your-bucket-name
```

### Issue: "No images found"
**Solution**:
```bash
# Check GCS bucket contents
gsutil ls gs://your-bucket/input_kids_monster/
gsutil ls gs://your-bucket/generated_images/

# Verify prefixes match command arguments
```

### Issue: "Import errors"
**Solution**:
```bash
# Make sure you're in project root
cd /Users/nicholasbaro/Python/semant

# Install dependencies
pip install -r requirements.txt
```

---

## ✅ Verification Checklist

Before running demo:
- [ ] Python 3.11+ installed
- [ ] Qdrant running on port 6333
- [ ] GCS credentials configured
- [ ] GCS bucket accessible
- [ ] Images exist in bucket
- [ ] Dependencies installed

After generation:
- [ ] HTML file created
- [ ] Images downloaded
- [ ] Story text generated
- [ ] Book opens in browser
- [ ] No errors in console

---

## 🎯 Quick Reference

### One-Liner Demo
```bash
python scripts/generate_childrens_book.py --bucket bahroo_public && open $(ls -t generated_books/*/book.html | head -1)
```

### View Existing Books
```bash
# List all generated books
ls -1 quacky_book_output/

# View a specific book
cat quacky_book_output/quacky_20250922_142953/quacky_book.md
```

### Check Generation Status
```bash
# View recent generation logs
tail -50 /tmp/semant_server.log

# Check Qdrant status
curl http://localhost:6333/collections/childrens_book_images
```

---

**Ready to generate?** Run the command above and watch the magic happen! ✨

