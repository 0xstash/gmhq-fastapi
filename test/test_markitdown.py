from markitdown import MarkItDown
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

md = MarkItDown()
result = md.convert("test/data/robinhood.pdf")

print(result.text_content)
