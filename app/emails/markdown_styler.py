import six
import bleach

from markdown import markdown as original_markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension


class InlineStylesTreeprocessor(Treeprocessor):
    """
    A treeprocessor that recursively applies inline styles
    to all elements of a given tree.
    """

    def __init__(self, styles):
        self.styles = styles

    def run(self, root):
        self.apply_styles(root)

    def apply_styles(self, element):
        for child in element:
            self.apply_styles(child)

        styles = self.styles.get(element.tag)

        if not styles:
            return

        styles = ' '.join(_.strip() for _ in styles.split())

        current_styles = element.get('style', '')
        new_styles = '%s %s' % (current_styles, styles)
        element.set('style', new_styles)


class InlineStylesExtension(Extension):
    """
    A Markdown extension for adding inline styles to
    elements, by tag name.
    """

    def __init__(self, **styles):
        self.styles = styles or {}

    def extendMarkdown(self, md, md_globals):
        md.treeprocessors['inline_styles'] = InlineStylesTreeprocessor(self.styles)


def markdown_with_inline_styles(object, styles_dictionary=None):
    """
    Converts the given object to Markdown, with inline
    styles suitable for email.
    """

    styles_dictionary = styles_dictionary or {}
    tags = bleach.sanitizer.ALLOWED_TAGS + ['p', 'span', 'h1', 'div']
    attributes = bleach.sanitizer.ALLOWED_ATTRIBUTES.copy()
    attributes.update({'div': ['style'], 'p': ['style'], 'h1': ['style']})
    styles = ['display', 'color', 'font-weight', 'font-size', 'border-radius', 'background', 'width', 'line-height',
              'padding', 'border', 'margin-right', 'margin']
    return bleach.clean(original_markdown(
        six.text_type(object),
        output_format="html5",
        extensions=[
            InlineStylesExtension(**styles_dictionary),
        ]),
        tags=tags,
        attributes=attributes,
        styles=styles
    )
