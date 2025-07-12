import base64
import copy
import random
import re
import string
from io import BytesIO

from PIL import Image


def parse_number(number_str: str):
    if isinstance(number_str, (int, float)):
        return number_str

    if number_str == "":
        return 0
    if number_str.endswith("½"):
        number_str = number_str[:-1] + ".5"

    return float(number_str.replace(",", ".").replace(" ", "").replace("'", ""))


def autofit_columns(ws):
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 3)
        ws.column_dimensions[column_letter].width = adjusted_width


def merge_dict(obj, template):
    obj = copy.deepcopy(obj) if isinstance(obj, dict) else {}
    for key, value in template.items():
        if isinstance(value, dict):
            obj[key] = merge_dict(obj.get(key, {}), value)
        else:
            obj[key] = obj.get(key, value)

    return obj


def base64_to_pil(base64_str: str, mode: str = "RGB"):
    base64_string = re.sub('^data:image/.+;base64,', '', base64_str)
    image_data = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_data))
    return image.convert(mode)


def random_string(length: int = 10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def contains_mako_syntax(s):
    mako_patterns = [
        r'\$\{.*?\}',      # ${...}
        r'<%.*?%>',        # <% ... %>
        r'^\s*%[^\n]+',    # % if ... or % for ... (line-based)
        r'##.*',           # Mako comment
    ]
    return any(re.search(pattern, s, re.MULTILINE | re.DOTALL) for pattern in mako_patterns)


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:  # shorthand hex
        hex_color = ''.join([c * 2 for c in hex_color])
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def contains_vietnamese(text):
    vietnamese_pattern = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ'
                                    r'ìíịỉĩòóọỏõôồốộổỗơờớợởỡ'
                                    r'ùúụủũưừứựửữỳýỵỷỹđ'
                                    r'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄ'
                                    r'ÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ'
                                    r'ÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]')
    return bool(vietnamese_pattern.search(text))
