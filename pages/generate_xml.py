import re
import xml.dom.minidom
import xml.etree.ElementTree as ET

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import unicodedata
from dash import Output, Input, ALL
from dash.exceptions import PreventUpdate

from components.table import table

FIELDS = {
    "PlayerUniqueId": "Id",
    "Name": "Name",
    "Lastname": "Last Name",
    "Firstname": "First Name",
    "Gender": "Gender",
    "Group": "Group",
    "Federation": "Federation",
    "Club": "Club",
}

df = pd.DataFrame({
    "": [1],
})

dash.register_page(
    __name__,
    path='/xml',
)

layout = dbc.Container([
    table(
        columns=[{
            "name": v,
            "id": k,
            "deletable": False,
            "selectable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
            "type": "text",
            "editable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
        } for k, v in FIELDS.items()],
        data=df.to_dict('records'),
    ),
    dbc.DropdownMenu([
        dbc.DropdownMenuItem(
            "Generate all", id="generate_all", n_clicks=0, className="me-1"
        ),
    ], label="Generate", class_name="p-0", id="generate_menu"),
    dash.dcc.Download(id="download-text"),
], className="flex flex-col gap-2 p-0")


@dash.callback(
    Output("table", "row_deletable"),
    Input("table", "data"),
)
def row_deletable(data):
    return len(data) > 1


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Output("generate_menu", "children"),
    Input("table", "data"),
    Input("generate_menu", "children"),
    prevent_initial_call=True,
)
def change_data(data, children):
    if not data:
        raise PreventUpdate

    group = set()

    data = [row for row in data if row.get("Name", None)]
    for i, row in enumerate(data):
        row["PlayerUniqueId"] = i + 1
        if row.get("Name", None):
            name = re.sub(r"\(.*\)", '', unicodedata.normalize('NFC', row["Name"])).strip()
            name = ' '.join(map(lambda s: s.capitalize(), name.lower().split())).split()

            if len(name) == 1:
                row["Lastname"], row["Firstname"] = "", name[0]
            else:
                row["Lastname"], row["Firstname"] = name[0], " ".join(name[1:])
        else:
            row["Lastname"], row["Firstname"] = "", ""

        if row.get("Group", None):
            group.add(row["Group"])

    if not data:
        data = [{"": 1}]
    else:
        data.append({k: "" for k in FIELDS.keys()})

    return data, [children[0], *[dbc.DropdownMenuItem(
        f"Generate group {name}", id={"type": f"generate_group", "index": name}, n_clicks=0, className="me-1"
    ) for name in group]]


@dash.callback(
    Input({"type": "generate_group", "index": ALL}, "n_clicks"),
)
def generate_group(n_clicks):
    print(n_clicks)


@dash.callback(
    Output("download-text", "data"),
    Input("generate_all", "n_clicks"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def download_text(n_clicks, data):
    if dash.ctx.triggered_id != "generate_all":
        raise PreventUpdate

    root = ET.Element('Players')
    for row in data:
        player = ET.SubElement(root, 'Player')
        for k, v in row.items():
            if not v or not k or k == "Name":
                continue
            player.set(k, str(v))

    tree = ET.ElementTree(root)
    result_str = ET.tostring(tree.getroot(), encoding="utf8").decode("utf8")

    print(result_str)

    dom = xml.dom.minidom.parseString(result_str)
    pretty_xml_as_string = dom.toprettyxml()

    return dict(content=pretty_xml_as_string, filename="output.xml")
