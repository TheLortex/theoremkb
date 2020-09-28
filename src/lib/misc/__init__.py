import re, os, math
from lxml import etree as ET

from .namespaces import *


def get_text(node: ET.Element) -> str:

    result = ""

    if node.tag == f"{ALTO}String":
        result = node.get("CONTENT")
    elif node.tag == f"{ALTO}SP":
        result = " "

    for children in node:
        result += get_text(children)

    if node.tag == f"{ALTO}TextLine":
        result += "\n"

    return result


REG_NOT_LETTER_OR_NUMBER = re.compile("[^a-zA-Z0-9 ]")
REG_NUMBERS = re.compile("[0-9]")


def get_pattern(text):
    text = REG_NOT_LETTER_OR_NUMBER.sub("", text)
    text = REG_NUMBERS.sub("@", text)
    return text.lower()


def remove_prefix(k: str):
    if "}" in k:
        return k.split("}")[1]
    else:
        return k


def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def filter_nan(obj):
    res = {}
    for k, v in obj.items():
        if type(v) == dict:
            res[k] = filter_nan(v)
        elif not (type(v) == float and math.isnan(v)):
            res[k] = v

    return res
