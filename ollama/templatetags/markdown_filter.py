from django import template
from django.utils.safestring import mark_safe
import markdown as md
import logging
import re
import uuid
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


logger = logging.getLogger(__name__)
register = template.Library()

LANG_NAMES = {
    'python': 'Python',
    'javascript': 'JavaScript',
    'html': 'HTML',
    'css': 'CSS',
    'java': 'Java',
    'cpp': 'C++',
    'go': 'Go',
}


def process_code_blocks(text: str) -> list:
    """
    Process code blocks in the given text.

    Args:
        text (str): The text to process.

    Returns:
        list: A list of tuples containing the processed code blocks.
    """
    pattern = re.compile(
        r'(?P<code>```(?P<lang>\w+)\n(?P<content>.*?)\n```)',
        re.DOTALL
    )
    parts = []
    last_end = 0

    for match in pattern.finditer(text):
        start = match.start()
        if start > last_end:
            parts.append(('text', text[last_end:start]))

        lang = match.group('lang').lower()
        code_content = match.group('content')
        parts.append(('code', lang, code_content))
        last_end = match.end()

    if last_end < len(text):
        parts.append(('text', text[last_end:]))

    return parts

@register.filter(name='markdown')
def markdown_filter(text: str):
    try:
        processed_parts = []
        parts = process_code_blocks(text)

        for part in parts:
            if part[0] == 'text':
                html = md.markdown(part[1], extensions=['tables', 'extra'])
                processed_parts.append(html)
            elif part[0] == 'code':
                lang, code = part[1], part[2]
                block_id = f'code-{uuid.uuid4().hex[:8]}'  # Уникальный ID для блока

                try:
                    lexer = get_lexer_by_name(lang, stripall=True)
                except:
                    lexer = get_lexer_by_name('text')

                formatter = HtmlFormatter(
                    cssclass='codehilite',
                    linenos=False,
                    style='default'
                )

                highlighted = highlight(code, lexer, formatter)
                header = (
                    f'<div class="code-header">'
                    f'<span>{LANG_NAMES.get(lang, lang.upper())}</span>'
                    f'<div class="code-actions">'
                    f'<button class="btn btn-primary mt-3 copy-btn" data-clipboard-target="#{block_id}">Copy</button>'
                    f'<button class="btn btn-primary mt-3 download-btn" data-target="#{block_id}" data-lang="{lang}">Download</button>'
                    f'</div>'
                    f'</div>'
                )
                processed_parts.append(
                    f'{header}'
                    f'<div id="{block_id}" class="code-block">'
                    f'{highlighted}'
                    f'</div>'
                )

        final_html = '\n'.join(processed_parts)
        return mark_safe(f'<div class="markdown-content">{final_html}</div>')
    except Exception as e:
        logger.error(f"Markdown processing error: {str(e)}")
        return mark_safe(f"<pre>{text}</pre>")