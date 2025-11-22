import os
from pathlib import Path
import json
from datetime import datetime

GENERATED_BOOKS_DIR = Path("generated_books")
STATIC_DIR = Path("static")
GALLERY_HTML_PATH = STATIC_DIR / "gallery.html"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Books Gallery</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .book-card {{ transition: transform 0.2s; }}
        .book-card:hover {{ transform: translateY(-5px); }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800">Generated Books Gallery</h1>
            <a href="/" class="text-blue-500 hover:text-blue-700">Back to Home</a>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {books_html}
        </div>
    </div>
</body>
</html>
"""

BOOK_CARD_TEMPLATE = """
            <div class="book-card bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
                <div class="h-48 bg-gray-200 flex items-center justify-center overflow-hidden">
                    {cover_html}
                </div>
                <div class="p-4 flex-grow flex flex-col justify-between">
                    <div>
                        <h3 class="text-xl font-semibold mb-2 truncate" title="{title}">{title}</h3>
                        <p class="text-sm text-gray-500 mb-4">{date}</p>
                    </div>
                    <a href="{link}" target="_blank" class="block w-full text-center bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition">Read Book</a>
                </div>
            </div>
"""

def get_cover_html(book_dir, book_url_path):
    # Try to find a cover image
    potential_covers = list(book_dir.glob("*.png")) + list(book_dir.glob("*.jpg"))
    if potential_covers:
        # Sort to maybe get the first one? or look for 'cover' in name
        # For now, just take the first image found
        cover_img = sorted(potential_covers)[0]
        img_url = f"{book_url_path}/{cover_img.name}"
        return f'<img src="{img_url}" alt="Book Cover" class="w-full h-full object-cover">'
    
    return '<span class="text-gray-400 text-4xl">📚</span>'

def generate_gallery():
    books = []
    
    if not GENERATED_BOOKS_DIR.exists():
        print(f"Directory {GENERATED_BOOKS_DIR} not found.")
        return

    # Scan for directories containing book.html or similar
    for entry in sorted(GENERATED_BOOKS_DIR.iterdir(), reverse=True):
        if entry.is_dir():
            book_file = entry / "book.html"
            if not book_file.exists():
                book_file = entry / "index.html"
            
            if book_file.exists():
                # It's a book!
                book_name = entry.name
                
                # Try to parse date from name
                # Formats: book_YYYYMMDD_HHMMSS or childrens_book_YYYYMMDD_HHMMSS
                date_str = "Unknown Date"
                try:
                    # extract date part
                    parts = book_name.split('_')
                    if len(parts) >= 2:
                        date_part = parts[-2]
                        time_part = parts[-1]
                        if len(date_part) == 8 and len(time_part) == 6:
                             dt = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
                             date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

                title = book_name.replace('_', ' ').title()
                link = f"/books/{book_name}/{book_file.name}"
                
                books.append({
                    "title": title,
                    "date": date_str,
                    "link": link,
                    "dir": entry,
                    "url_path": f"/books/{book_name}"
                })
        elif entry.is_file() and entry.suffix == '.html':
            # Standalone HTML files
             title = entry.stem.replace('_', ' ').title()
             link = f"/books/{entry.name}"
             books.append({
                    "title": title,
                    "date": "Unknown",
                    "link": link,
                    "dir": GENERATED_BOOKS_DIR, # Just use root for cover search? probably no cover for standalone
                    "url_path": "/books"
             })

    books_html = ""
    for book in books:
        # Determine cover
        cover_html = '<span class="text-gray-400 text-4xl">📚</span>'
        if book['dir'] != GENERATED_BOOKS_DIR:
             cover_html = get_cover_html(book['dir'], book['url_path'])
        
        books_html += BOOK_CARD_TEMPLATE.format(
            title=book['title'],
            date=book['date'],
            link=book['link'],
            cover_html=cover_html
        )

    with open(GALLERY_HTML_PATH, "w") as f:
        f.write(HTML_TEMPLATE.format(books_html=books_html))
    
    print(f"Gallery generated at {GALLERY_HTML_PATH} with {len(books)} books.")

if __name__ == "__main__":
    generate_gallery()

