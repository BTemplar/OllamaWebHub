from django import template
from django.utils.safestring import mark_safe
import markdown as md
import logging
import re
import uuid
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

# Setting up a logger for tracking errors in the filter
logger = logging.getLogger(__name__)
# Registering a filter in the Django template engine
register = template.Library()


def process_code_blocks(text: str) -> list:
    """
    Processes code blocks in the given text.

    Args:
        text (str): The text to process.

    Returns:
        list: A list of tuples containing the processed code blocks.
    """
    # Regular expression for searching code blocks:
    # - `` - the beginning of the block
    # - (\w+) - programming language
    # - (.*?) - code content (unreliable capture)
    # - `` - end of block
    pattern = re.compile(
        r'(?P<code>```(?P<lang>\w+)\n(?P<content>.*?)\n```)',
        re.DOTALL  # Ignores line breaks in the template
    )

    parts = []
    last_end = 0

    # Iterate over all found code blocks
    for match in pattern.finditer(text):
        start = match.start()
        # If there is text between the previous block and the current one
        if start > last_end:
            parts.append(('text', text[last_end:start]))

        # Extracting information about a block of code
        lang = match.group('lang').lower()
        code_content = match.group('content')
        parts.append(('code', lang, code_content))
        last_end = match.end()

    # Adding the remaining text after the last block
    if last_end < len(text):
        parts.append(('text', text[last_end:]))

    return parts


@register.filter(name='markdown')
def markdown_filter(text: str):
    """
    Converts a markdown text to HTML.

    Args:
        text (str): The markdown text to convert.

    Returns:
        str: The converted HTML.
    """
    try:
        processed_parts = []
        parts = process_code_blocks(text)

        # Processing of each part of the text
        for part in parts:
            if part[0] == 'text':
                # Plain text: convert to HTML using markdown
                html = md.markdown(part[1], extensions=['tables', 'extra'])
                processed_parts.append(html)
            elif part[0] == 'code':
                # Code block: we highlight syntactically and add an interface
                lang, code = part[1], part[2]

                # Generate a unique ID for each code block
                block_id = f'code-{uuid.uuid4().hex[:8]}'

                try:
                    # Getting a lexer for a programming language
                    # If the language is not supported, use 'text' as default
                    lexer = get_lexer_by_name(lang, stripall=True)
                    lang_name = lexer.name
                except:
                    lexer = get_lexer_by_name('text')
                    lang_name = lang if lang else "Code"

                # Setting up formatting to highlight the code
                formatter = HtmlFormatter(
                    cssclass='codehilite',
                    linenos=False,
                    style='default'
                )

                # Code extraction using pygments
                highlighted = highlight(code, lexer, formatter)

                # Create a header with buttons for copying and uploading
                header = (
                    f'<div class="code-header">'
                    f'<span>{lang_name}</span>'
                    f'<div class="code-actions">'
                    f'<button class="btn btn-primary mt-3 copy-btn" data-clipboard-target="#{block_id}">Copy</button>'
                    f'<button class="btn btn-primary mt-3 download-btn" data-target="#{block_id}" data-lang="{lang}">Download</button>'
                    f'</div>'
                    f'</div>'
                )

                # Adding the processed code block to the result
                processed_parts.append(
                    f'{header}'
                    f'<div id="{block_id}" class="code-block">'
                    f'{highlighted}'
                    f'</div>'
                )

        # Combining all the parts into the final HTML
        final_html = '\n'.join(processed_parts)
        return mark_safe(f'<div class="markdown-content">{final_html}</div>')

    except Exception as e:
        # Logging errors during Markdown processing
        logger.error(f"Markdown processing error: {str(e)}")
        # Return text in <pre> format as an alternative option
        return mark_safe(f"<pre>{text}</pre>")
