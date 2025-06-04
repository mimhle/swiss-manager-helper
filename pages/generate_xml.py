import base64
import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
from io import BytesIO
from operator import itemgetter

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import unicodedata
from dash import Output, Input, ALL, State, html, dcc
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
    dcc.Upload(
        dbc.Button([html.I(className="bi bi-box-arrow-in-down-right"), " Import from Excel"], className="w-fit"),
        id="excel_upload_btn",
        accept="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel",
    ),
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
                        dbc.Col(
                            dbc.Button("Auto fill team", id="fill_team", n_clicks=0, color="secondary", disabled=True,
                                       className="me-1 w-fit"), width="auto"),
                        dbc.Col(
                            dbc.Button("Auto fill club", id="fill_club", n_clicks=0, color="secondary", disabled=True,
                                       className="me-1 w-fit"), width="auto"),
                        dbc.Col(dbc.Button("Auto fill federation", id="fill_federation", n_clicks=0, color="secondary",
                                           disabled=True, className="me-1 w-fit"), width="auto"),
                        dbc.Col(dbc.Button([html.I(className="bi bi-download"), " Generate teams.xml"], id="generate_team", n_clicks=0, color="secondary",
                                           disabled=True, className="me-1 w-fit"), width="auto"),
                    ]),
                ], className="flex flex-col gap-2 p-0"), title="Auto fill club and team"
            ),
        ],
        start_collapsed=True
    ),
    dbc.Row([
        dbc.Button("Auto fill group", id="fill_group", n_clicks=0, color="secondary", className="w-fit"),
        dbc.Button([html.I(className="bi bi-trash"), " Clear"], id="clear_btn", n_clicks=0, color="danger", className="w-fit"),
    ], className="flex flex-row gap-2 p-0 m-0"),
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
            "Generate all", id="generate_all", n_clicks=0, className=""
        ),
    ], label=[html.I(className="bi bi-download"), " Generate"], class_name="p-0", id="generate_menu"),
    dash.dcc.Download(id="download-text"),
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Import from Excel"),),
            dbc.ModalBody("This is the content of the modal", id="excel_import_modal_body"),
            dbc.ModalFooter(
                dbc.Button("Import", id="excel_import_btn", className="ml-auto", n_clicks=0)
            ),
        ],
        id="excel_import_modal",
        is_open=False,
        size="xl",
        backdrop="static",
        scrollable=True
    ),
], className="flex flex-col gap-2 p-0")


@dash.callback(
    Output("table", "data", allow_duplicate=True),
    Input("clear_btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_table(n_clicks):
    if not n_clicks or dash.ctx.triggered_id != "clear_btn":
        raise PreventUpdate

    return [{"": 1}]


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
        data = list(unique(sorted([row for row in data if row.get("Federation", None) != ""],
                                  key=lambda x: sum(v is None for v in x.values())),
                           key=lambda x: x.get("Federation", "")))

        data = data + temp

        for i, row in enumerate(data):
            row["TeamUniqueId"] = i + 1

        data.append({k: "" for k in FIELDS.keys()})

    return data, not any([row.get("Federation", None) for row in data]), not any(
        [row.get("TeamUniqueId", None) for row in data]), not any(
        [row.get("Federation", None) for row in data]), not any([row.get("TeamUniqueId", None) for row in data])


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

    data_group = {row["Federation"]: row["Club"] for row in data_group if
                  row.get("Federation", None) and row.get("Club", None)}

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

    data_group = {row["Federation"]: row["TeamUniqueId"] for row in data_group if
                  row.get("Federation", None) and row.get("TeamUniqueId", None)}

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

    data_group = {row["Club"]: row["Federation"] for row in data_group if
                  row.get("Club", None) and row.get("Federation", None)}

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
        f"Generate group {name}", id={"type": "generate_group", "index": name}, n_clicks=0, className="me-1", key=name
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


def read_excel(content: str) -> pd.DataFrame:
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(BytesIO(decoded))
    return df


@dash.callback(
    [
        Output("excel_import_modal", "is_open", allow_duplicate=True),
        Output("excel_import_modal_body", "children"),
        Output("excel_upload_btn", "contents")
    ],
    [Input("excel_upload_btn", "contents")],
    [State('excel_upload_btn', 'filename')],
    prevent_initial_call=True,
)
def toggle_excel_import_modal(contents, filename):
    if not contents:
        raise PreventUpdate
    data = read_excel(contents)
    empty_row = pd.DataFrame([None] * len(data.columns), index=data.columns).T
    data = pd.concat([empty_row, data], ignore_index=True)
    data.reset_index(inplace=True)
    data.rename(columns={'index': 'No'}, inplace=True)
    return (
        True,
        dash.dash_table.DataTable(
            id={"type": "import_table", "index": "excel_import_table"},
            columns=[{
                "name": col,
                "id": col,
                "presentation": "dropdown",
            } for col in data.columns],
            hidden_columns=["No"],
            data=data.to_dict('records'),
            editable=True,
            filter_action="none",
            sort_action="none",
            row_selectable=False,
            row_deletable=False,
            page_current=0,
            page_size=999,
            style_cell={'textAlign': 'left'},
            style_header={
                'whiteSpace': 'normal',
                'height': 'auto',
            },
            style_data={
                'whiteSpace': 'normal',
                'height': 'auto',
            },
            style_data_conditional=[
                {
                    "if": {"filter_query": "{No} ne 0"},
                    "pointerEvents": "none",
                },
                {
                    "if": {"filter_query": "{No} eq 0"},
                    "backgroundColor": "#f2f2f2",
                    "fontWeight": "bold",
                },
            ],
            dropdown_conditional=[{
                'if': {
                    'column_id': col,
                    'filter_query': '{No} eq 0'
                },
                "clearable": True,
                'options': [{'label': v, 'value': v} for k, v in FIELDS.items() if k not in ("PlayerUniqueId", "Firstname", "Lastname")],
            } for col in data.columns if col != "No"],
        ),
        None
    )


@dash.callback(
    [
        Output("excel_import_modal", "is_open", allow_duplicate=True),
        Output("table", "data", allow_duplicate=True),
    ],
    Input("excel_import_btn", "n_clicks"),
    State({'type': 'import_table', 'index': ALL}, "data"),
    prevent_initial_call=True,
)
def import_excel(n_clicks, data):
    if not data or not data[0]:
        raise PreventUpdate

    data = data[0]
    data = pd.DataFrame(data)
    first_row = data.iloc[0]
    data = data.iloc[1:].reset_index(drop=True)

    for col in first_row.keys():
        if first_row[col] and first_row[col] in FIELDS:
            data.rename(columns={col: FIELDS[first_row[col]]}, inplace=True)
        else:
            del data[col]

    return False, data.to_dict('records')
