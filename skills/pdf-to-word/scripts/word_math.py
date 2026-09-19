"""Small OOXML math builders for formulas manually verified against a source."""
from docx.oxml import OxmlElement

def text(value):
    run=OxmlElement('m:r');node=OxmlElement('m:t')
    node.text=str(value);run.append(node)
    return run

def _container(tag, values):
    node=OxmlElement(tag)
    if isinstance(values,str):values=[values]
    for value in values:node.append(text(value) if isinstance(value,str) else value)
    return node

def subscript(base,index):
    node=OxmlElement('m:sSub')
    node.extend([_container('m:e',base),_container('m:sub',index)])
    return node

def superscript(base,index):
    node=OxmlElement('m:sSup')
    node.extend([_container('m:e',base),_container('m:sup',index)])
    return node

def fraction(numerator,denominator):
    node=OxmlElement('m:f')
    node.extend([_container('m:num',numerator),_container('m:den',denominator)])
    return node

def append_equation(paragraph,parts):
    """Pass strings or newly created elements; OOXML nodes cannot be reused."""
    node=_container('m:oMath',parts)
    paragraph._p.append(node)
    # Fraction height must not be clipped by exact paragraph line spacing.
    paragraph.paragraph_format.line_spacing=1.25
    return node
