import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
from operator import itemgetter

import dash
import dash_bootstrap_components as dbc
import unicodedata
from dash import Output, Input, ALL, State
from dash.exceptions import PreventUpdate
from toolz import unique

from components.table import table

FIELDS = {
    "PlayerUniqueId": "Id",
    "Name": "Name",
    "Lastname": "Last Name",
    "Firstname": "First Name",
    "Gender": "Gender",
    "Group": "Group",
    "Rating": "Rating",
    "Title": "Title",
    "Federation": "Federation",
    "FIDEId": "FIDE Id",
    "Club": "Club",
    "TeamUniqueId": "Team Id",
}

dash.register_page(
    __name__,
    path='/xml',
)

layout = dbc.Container([
    dbc.Button("Auto fill group", id="fill_group", n_clicks=0, color="secondary", className="me-1 w-fit"),
    dbc.Accordion(
        [
            dbc.AccordionItem(
                dbc.Container([
                    table(
                        id="table_group",
                        columns=[{
                            "name": FIELDS["TeamUniqueId"],
                            "id": "TeamUniqueId",
                            "deletable": False,
                            "selectable": True,
                            "type": "text",
                            "editable": False,
                        }, {
                            "name": FIELDS["Federation"],
                            "id": "Federation",
                            "deletable": False,
                            "selectable": True,
                            "type": "text",
                            "editable": True,
                        }, {
                            "name": FIELDS["Club"],
                            "id": "Club",
                            "deletable": False,
                            "selectable": True,
                            "type": "text",
                            "editable": True,
                        }],
                        data=[{"": 1}],
                        style_cell_conditional=[
                            {'if': {'column_id': 'Federation'}, 'width': '30%'},
                            {'if': {'column_id': 'TeamUniqueId'}, 'width': '8%'},
                        ]
                    ),
                    dbc.Row([
                        dbc.Col(dbc.Button("Auto fill team", id="fill_team", n_clicks=0, color="secondary", disabled=True, className="me-1 w-fit"), width="auto"),
                        dbc.Col(dbc.Button("Auto fill club", id="fill_club", n_clicks=0, color="secondary", disabled=True, className="me-1 w-fit"), width="auto"),
                        dbc.Col(dbc.Button("Auto fill federation", id="fill_federation", n_clicks=0, color="secondary", disabled=True, className="me-1 w-fit"), width="auto"),
                        dbc.Col(dbc.Button("Generate teams.xml", id="generate_team", n_clicks=0, color="secondary", disabled=True, className="me-1 w-fit"), width="auto"),
                    ]),
                ], className="flex flex-col gap-2 p-0"), title="Auto fill club and team"
            ),
        ],
        start_collapsed=True
    ),
    table(
        id="table",
        columns=[{
            "name": v,
            "id": k,
            "deletable": False,
            "selectable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
            "type": "text",
            "editable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
        } for k, v in FIELDS.items()] + [{
            "name": "Duplicate",
            "id": "duplicate",
        }],
        hidden_columns=["duplicate"],
        data=[{"": 1}],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{duplicate} = "true"',
                },
                'backgroundColor': '#f2ff0030',
            }
        ]
    ),
    dbc.DropdownMenu([
        dbc.DropdownMenuItem(
            "Generate all", id="generate_all", n_clicks=0, className="me-1"
        ),
    ], label="Generate", class_name="p-0", id="generate_menu"),
    dash.dcc.Download(id="download-text"),
], className="flex flex-col gap-2 p-0")


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Input("fill_group", "n_clicks"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def fill_group(n_clicks, data):
    if not data or dash.ctx.triggered_id != "fill_group":
        raise PreventUpdate

    for row in data:
        if row.get("Gender", None):
            print(row.get("Gender", "").strip().lower())
            match row.get("Gender", "").strip().lower():
                case "m" | "male" | "man" | "nam":
                    row["Group"] = "m"
                case "f" | "female" | "women" | "nu" | "nữ":
                    row["Group"] = "f"
        else:
            row["Group"] = "m"

    return data


@dash.callback(
    Output("table_group", "data", allow_duplicate=True),
    Output("fill_club", "disabled"),
    Output("fill_team", "disabled"),
    Output("fill_federation", "disabled"),
    Output("generate_team", "disabled"),
    Input("table_group", "data"),
    prevent_initial_call=True,
)
def change_data(data):
    if not data:
        data = [{"": 1}]
    else:
        data = [row for row in data if any(row.values())]

        temp = [row for row in data if row.get("Federation", None) == ""]
        data = list(unique(sorted([row for row in data if row.get("Federation", None) != ""], key=lambda x: sum(v is None for v in x.values())), key=lambda x: x.get("Federation", "")))

        data = data + temp

        for i, row in enumerate(data):
            row["TeamUniqueId"] = i + 1

        data.append({k: "" for k in FIELDS.keys()})

    return data, not any([row.get("Federation", None) for row in data]), not any([row.get("TeamUniqueId", None) for row in data]), not any([row.get("Federation", None) for row in data]), not any([row.get("TeamUniqueId", None) for row in data])


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Input("fill_club", "n_clicks"),
    Input("table_group", "data"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def fill_club(n_clicks, data_group, data):
    if not data or dash.ctx.triggered_id != "fill_club":
        raise PreventUpdate

    data_group = {row["Federation"]: row["Club"] for row in data_group if row.get("Federation", None) and row.get("Club", None)}

    for row in data:
        if row.get("Federation", None):
            row["Club"] = data_group.get(row["Federation"], "")

    return data


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Input("fill_team", "n_clicks"),
    Input("table_group", "data"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def fill_team(n_clicks, data_group, data):
    if not data or dash.ctx.triggered_id != "fill_team":
        raise PreventUpdate

    data_group = {row["Federation"]: row["TeamUniqueId"] for row in data_group if row.get("Federation", None) and row.get("TeamUniqueId", None)}

    for row in data:
        if row.get("Federation", None):
            row["TeamUniqueId"] = data_group.get(row["Federation"], "")

    return data


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Input("fill_federation", "n_clicks"),
    Input("table_group", "data"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def fill_federation(n_clicks, data_group, data):
    if not data or dash.ctx.triggered_id != "fill_federation":
        raise PreventUpdate

    data_group = {row["Club"]: row["Federation"] for row in data_group if row.get("Club", None) and row.get("Federation", None)}

    for row in data:
        if row.get("Club", None):
            row["Federation"] = data_group.get(row["Club"], "")

    return data


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Output("generate_menu", "children"),
    Input("table", "data"),
    State("generate_menu", "children"),
    prevent_initial_call=True,
)
def change_data(data, children):
    group = set()

    data = [row for row in data if row.get("Name", None)]
    name_dict = dict()
    for i, row in enumerate(data):
        for k, v in row.items():
            row[k] = v.strip() if isinstance(v, str) else v

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

        row["duplicate"] = "false"
        if f"{row['Lastname']} {row['Firstname']}" in name_dict:
            row["duplicate"] = "true"
            name_dict[f"{row['Lastname']} {row['Firstname']}"]["duplicate"] = "true"
        else:
            name_dict[f"{row['Lastname']} {row['Firstname']}"] = row

        if row.get("Group", None):
            group.add(row["Group"])

    if not data:
        data = [{"": 1}]
    else:
        data.append({k: "" for k in FIELDS.keys()})

    return data, [children[0], *[dbc.DropdownMenuItem(
        f"Generate group {name}", id={"type": f"generate_group", "index": name}, n_clicks=0, className="me-1", key=name
    ) for name in group]]


def generate_players_xml(data, group=None):
    root = ET.Element('Players')
    for row in data:
        if group:
            if row.get("Group", None) != group:
                continue

        player = ET.SubElement(root, 'Player')
        for k, v in row.items():
            if not v or not k or k == "Name" or k not in FIELDS:
                continue
            player.set(k, str(v))

    tree = ET.ElementTree(root)
    result_str = ET.tostring(tree.getroot(), encoding="utf8").decode("utf8")

    dom = xml.dom.minidom.parseString(result_str)
    pretty_xml_as_string = dom.toprettyxml()

    return pretty_xml_as_string


def generate_teams_xml(data):
    root = ET.Element('Teams')
    for row in data:
        team = ET.SubElement(root, 'Team')
        team.set("TeamLongname", row.get("Club", ""))
        team.set("TeamShortname", row.get("Federation", ""))
        team.set("TeamUniqueId", str(row.get("TeamUniqueId", "")))

    tree = ET.ElementTree(root)
    result_str = ET.tostring(tree.getroot(), encoding="utf8").decode("utf8")

    dom = xml.dom.minidom.parseString(result_str)
    pretty_xml_as_string = dom.toprettyxml()

    return pretty_xml_as_string


@dash.callback(
    Output("download-text", "data", allow_duplicate=True),
    Input("generate_team", "n_clicks"),
    Input("table_group", "data"),
    prevent_initial_call=True,
)
def generate_team(n_clicks, data):
    if dash.ctx.triggered_id != "generate_team":
        raise PreventUpdate

    data = [row for row in data if row.get("TeamUniqueId", None)]
    data = sorted(data, key=itemgetter("TeamUniqueId"))

    pretty_xml_as_string = generate_teams_xml(data)

    return dict(content=pretty_xml_as_string, filename="teams.xml")


@dash.callback(
    Output("download-text", "data", allow_duplicate=True),
    Output({'type': 'generate_group', 'index': ALL}, 'n_clicks'),
    Input({'type': 'generate_group', 'index': ALL}, 'n_clicks'),
    Input("table", "data"),
    prevent_initial_call=True,
)
def generate_group(n_clicks, data):
    if dash.ctx.triggered_id == "table":
        raise PreventUpdate

    pretty_xml_as_string = generate_players_xml(data, group=dash.ctx.triggered_id["index"])

    return dict(content=pretty_xml_as_string, filename=f"{dash.ctx.triggered_id['index']}.xml"), n_clicks


@dash.callback(
    Output("download-text", "data", allow_duplicate=True),
    Input("generate_all", "n_clicks"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def download_text(n_clicks, data):
    if dash.ctx.triggered_id != "generate_all":
        raise PreventUpdate

    pretty_xml_as_string = generate_players_xml(data)

    return dict(content=pretty_xml_as_string, filename="output.xml")
