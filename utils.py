def parse_number(number_str: str):
    if isinstance(number_str, (int, float)):
        return number_str

    if number_str == "":
        return 0
    if number_str.endswith("½"):
        number_str = number_str[:-1] + ".5"

    return float(number_str.replace(",", ".").replace(" ", "").replace("'", ""))