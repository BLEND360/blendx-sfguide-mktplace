#!/usr/bin/env python3
"""
Generate PDF documentation from Markdown file.
Requires: pip install markdown weasyprint
"""

import markdown
from pathlib import Path

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @top-center {{
                content: "BlendX Documentation";
                font-size: 10px;
                color: #666;
            }}
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10px;
                color: #666;
            }}
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
        }}

        h1 {{
            color: #1a73e8;
            font-size: 28pt;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
            margin-top: 30px;
            page-break-after: avoid;
        }}

        h2 {{
            color: #1a73e8;
            font-size: 18pt;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
            margin-top: 25px;
            page-break-after: avoid;
        }}

        h3 {{
            color: #333;
            font-size: 14pt;
            margin-top: 20px;
            page-break-after: avoid;
        }}

        h4 {{
            color: #555;
            font-size: 12pt;
            margin-top: 15px;
            page-break-after: avoid;
        }}

        p {{
            margin: 10px 0;
        }}

        code {{
            background-color: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 10pt;
        }}

        pre {{
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 9pt;
            line-height: 1.4;
            page-break-inside: avoid;
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
            color: #f8f8f2;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10pt;
            page-break-inside: avoid;
        }}

        th {{
            background-color: #1a73e8;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            border: 1px solid #ddd;
            padding: 10px;
            vertical-align: top;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        ul, ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}

        li {{
            margin: 5px 0;
        }}

        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}

        blockquote {{
            border-left: 4px solid #1a73e8;
            margin: 15px 0;
            padding: 10px 20px;
            background-color: #f5f9ff;
        }}

        .cover-page {{
            text-align: center;
            padding-top: 200px;
            page-break-after: always;
        }}

        .cover-page h1 {{
            font-size: 36pt;
            border: none;
            color: #1a73e8;
        }}

        .cover-page .subtitle {{
            font-size: 18pt;
            color: #666;
            margin-top: 20px;
        }}

        .cover-page .version {{
            font-size: 12pt;
            color: #999;
            margin-top: 50px;
        }}

        strong {{
            color: #1a73e8;
        }}

        a {{
            color: #1a73e8;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        img, svg {{
            max-width: 100%;
            height: auto;
            overflow: visible;
        }}

        pre > code {{
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="cover-page">
        <h1>BlendX</h1>
        <div class="subtitle">CrewAI Agent Workflows<br>Snowflake Native Application</div>
        <div class="version">Documentation v1.0<br>December 2025</div>
    </div>
    {content}
</body>
</html>
"""


def generate_pdf():
    """Generate PDF from Markdown documentation."""
    # Get project root (parent of scripts folder)
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"
    md_file = docs_dir / "BlendX_Documentation.md"
    pdf_file = docs_dir / "BlendX_Documentation.pdf"
    html_file = docs_dir / "BlendX_Documentation.html"

    # Read markdown content
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc"]
    )
    html_content = md.convert(md_content)

    # Create full HTML document
    full_html = HTML_TEMPLATE.format(content=html_content)

    # Save HTML (useful for debugging)
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML saved to: {html_file}")

    # Try to generate PDF with weasyprint
    try:
        from weasyprint import HTML

        HTML(string=full_html, base_url=str(docs_dir)).write_pdf(pdf_file)
        print(f"PDF generated successfully: {pdf_file}")
    except ImportError:
        print("\nWeasyPrint not installed. To generate PDF, run:")
        print("  pip install weasyprint")
        print("\nAlternatively, you can:")
        print("1. Open the HTML file in a browser")
        print("2. Use 'Print to PDF' feature")
        print(f"\nHTML file: {html_file}")


if __name__ == "__main__":
    generate_pdf()
