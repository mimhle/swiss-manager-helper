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
