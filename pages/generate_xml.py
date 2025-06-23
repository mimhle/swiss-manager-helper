import base64
import copy
import os
import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from operator import itemgetter

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import unicodedata
from PIL import Image, ImageDraw, ImageFont
from dash import Output, Input, ALL, State, html, dcc, clientside_callback
from dash.exceptions import PreventUpdate
from mako.template import Template
from toolz import unique

from components.table import table
from utils import base64_to_pil, random_string, hex_to_rgb

from datetime import datetime

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
    "Type": "Type",
}

TEMP_FOLDER = "./temp"
FONTS_FOLDER = "./fonts"

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

GLOBAL_CONTEXT = {
    "datetime": datetime,
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
        className="w-fit",
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
        dbc.Row([
            dbc.Button("Auto fill group", id="fill_group", n_clicks=0, color="secondary", className="w-fit"),
            dbc.Button([html.I(className="bi bi-trash"), " Clear"], id="clear_btn", n_clicks=0, color="danger", className="w-fit"),
        ], className="flex flex-row gap-2 p-0 m-0 w-fit"),
        html.A(html.I(className="bi bi-info-circle w-fit mt-auto", id="info_tooltip_icon"), href="https://docs.makotemplates.org/en/latest/syntax.html", target="_blank", className="w-fit mt-auto"),
        dbc.Tooltip(
            [
                html.P("- Mako syntax supported on all fields except for name.", className="text-left"),
                html.P("- Example: =${Group.lower()}", className="text-left"),
                html.P("- The syntax only available when editing the last row and will apply to all row.", className="text-left"),
                html.P("- Variable name is case insensitive.", className="text-left"),
            ],
            target="info_tooltip_icon",
        ),
    ], className="flex flex-row gap-2 p-0 m-0 justify-between"),
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
            },
        ]
    ),
    dbc.Row([
        dbc.DropdownMenu([
            dbc.DropdownMenuItem(
                "Generate all", id="generate_all", n_clicks=0, className=""
            ),
        ], label=[html.I(className="bi bi-download"), " Generate"], class_name="p-0 w-fit", id="generate_menu"),
        dbc.Button([html.I(className="bi bi-card-image"), " Generate player cards"], id="card_open_btn", n_clicks=0, color="secondary", className="w-fit"),
    ], className="flex flex-row gap-2 p-0 m-0"),
    dash.dcc.Download(id="download"),
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Import from Excel"),),
            dbc.ModalBody([
                dbc.InputGroup([
                    dbc.InputGroupText("Sheet:"),
                    dbc.Select(
                        id="excel_sheet_select",
                        options=[
                            {"label": "Sheet1", "value": "Sheet1"},
                        ],
                        value="Sheet1",
                    ),
                ], className="mb-2"),
                html.Div(id="excel_import_modal_body", className=""),
            ]),
            dbc.ModalFooter([
                dbc.Button("Import and append", id="excel_import_append_btn", className="", n_clicks=0),
                dbc.Button("Import and replace", id="excel_import_btn", className="", n_clicks=0),
            ], className="flex flex-row gap-2 justify-end"),
        ],
        id="excel_import_modal",
        is_open=False,
        size="xl",
        backdrop="static",
        scrollable=True
    ),
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Generate player cards"),),
            dbc.ModalBody(dbc.Spinner([
                dcc.Upload(
                    html.Div([
                        html.I(className="bi bi-image"),
                        ' Drag and Drop or ',
                        html.A('Select image')
                    ]),
                    id="card_template_upload_btn",
                    accept=".png, .jpg, .jpeg",
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '3px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                ),
                dcc.Upload(
                    html.Div([
                        html.I(className="bi bi-file-earmark-font"),
                        ' Drag and Drop or ',
                        html.A('Select font')
                    ]),
                    id="font_upload_btn",
                    accept=".ttf, .otf",
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '3px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                ),
            ], id="upload_loading")),
            dbc.ModalBody(html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Spinner(
                            html.Img(src="", className="w-full h-fit", id="card_preview_image"),
                        ),
                        dcc.Store("card_template_image_store", data="./static/card_template.png"),
                    ], width=8),
                    dbc.Col([
                        dbc.Row([
                            html.Div(
                                dcc.Upload(
                                    dbc.Button([html.I(className="bi bi-box-arrow-in-down-right"), " Import config"], size="sm", color="secondary"),
                                    id="card_template_import_config_btn",
                                    accept=".json",
                                    className="w-fit p-0",
                                ),
                                className="w-fit p-0",
                            ),
                            dbc.Button([html.I(className="bi bi-box-arrow-up-left"), " Export config"], id="card_template_export_config_btn", n_clicks=0, className="w-fit", size="sm", color="secondary"),
                        ], className="flex flex-row gap-1 m-0"),
                        html.Div(id="jsoneditor", className="w-full h-96"),
                        dbc.InputGroup([
                            dbc.InputGroupText("Preview"),
                            dbc.Select(
                                id="card_preview_select",
                                options=[
                                    {"label": "Id #1", "value": "1"},
                                ],
                            )
                        ], className=""),
                        dbc.Button([html.I(className="bi bi-arrow-clockwise"), " Update preview"], id="card_template_preview_update_btn", n_clicks=0, className="w-fit"),
                        dcc.Store("card_template_config"),
                    ], className="flex flex-col gap-1 h-fit"),
                ], className="mb-1"),
            ]), className="h-fit"),
            dbc.ModalFooter([
                dbc.Button([html.I(className="bi bi-file-earmark-image"), " Download current"], id="card_download_current_btn", className="ml-auto", n_clicks=0),
                dbc.Button([html.I(className="bi bi-file-earmark-zip"), " Download all"], id="card_download_all_btn", className="", n_clicks=0)
            ]),
        ],
        id="card_modal",
        is_open=False,
        size="xl",
        scrollable=False
    ),
], className="flex flex-col gap-2 p-0")


def generate_name(data: dict) -> dict:
    return data | {k.lower(): v for k, v in data.items()} | {FIELDS[k].lower().replace(" ", "_"): v for k, v in data.items() if k in FIELDS}


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

    name_dict = dict()
    for i, row in enumerate(data):
        for k, v in row.items():
            row[k] = v.strip().replace("\n", " ") if isinstance(v, str) else v

        row["PlayerUniqueId"] = i + 1
        if row.get("Name", None):
            name = re.sub(r"\(.*\)", '', unicodedata.normalize('NFC', row["Name"])).strip().replace(",", "")
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

    if len(data) > 1:
        for k, v in data[-1].items():
            v = str(v)
            if v.startswith("=") and k not in ("Name", "Lastname", "Firstname"):
                v = v[1:]
                for row in data[:-1]:
                    try:
                        row[k] = Template(v).render(**generate_name(row), **GLOBAL_CONTEXT)
                    except Exception:
                        try:
                            row[k] = Template(v + "}").render(**generate_name(row), **GLOBAL_CONTEXT)
                        except Exception as e:
                            if "NameError" in str(e) or "SyntaxException" in str(e):
                                row[k] = v
                            else:
                                row[k] = "#ERROR"
                                raise e

    data = [row for row in data if row.get("Name", None)]
    for row in data:
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
    Output("download", "data", allow_duplicate=True),
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
    Output("download", "data", allow_duplicate=True),
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
    Output("download", "data", allow_duplicate=True),
    Input("generate_all", "n_clicks"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def download_text(n_clicks, data):
    if dash.ctx.triggered_id != "generate_all":
        raise PreventUpdate

    pretty_xml_as_string = generate_players_xml(data)

    return dict(content=pretty_xml_as_string, filename="output.xml")


def read_excel(content: str, sheet: str | None) -> pd.DataFrame | dict[str, pd.DataFrame]:
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(BytesIO(decoded), sheet_name=sheet)
    return df


@dash.callback(
    [
        Output("excel_import_modal", "is_open", allow_duplicate=True),
        Output("excel_import_modal_body", "children"),
        Output("excel_sheet_select", "options"),
        Output("excel_sheet_select", "value"),
    ],
    [
        Input("excel_upload_btn", "contents"),
        Input("excel_sheet_select", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_excel_import_modal(contents, sheet):
    if not contents:
        raise PreventUpdate
    data = read_excel(contents, None)
    sheets = tuple(data.keys())
    if sheet in data.keys():
        data = data[sheet]
    else:
        sheet = sheets[0]
        data = data[sheet]

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
            row_deletable=True,
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
        [{"label": sheet, "value": sheet} for sheet in sheets],
        sheet if sheet in sheets else sheets[0],
    )


@dash.callback(
    Output("excel_upload_btn", "contents"),
    Input("excel_import_modal", "is_open"),
)
def close_excel_import_modal(is_open):
    if is_open:
        raise PreventUpdate

    return None


@dash.callback(
    [
        Output("excel_import_modal", "is_open", allow_duplicate=True),
        Output("table", "data", allow_duplicate=True),
    ],
    [
        Input("excel_import_btn", "n_clicks"),
        Input("excel_import_append_btn", "n_clicks"),
    ],
    [
        State({'type': 'import_table', 'index': ALL}, "data"),
        State("table", "data")
    ],
    prevent_initial_call=True,
)
def import_excel(n_clicks, n_clicks2, data, table_data):
    if not data or not data[0]:
        raise PreventUpdate

    data = data[0]
    data = pd.DataFrame(data)
    first_row = data.iloc[0]
    data = data.iloc[1:].reset_index(drop=True)

    if len([v for v in first_row.to_list() if v]) != len(set(v for v in first_row.to_list() if v)):
        raise PreventUpdate

    for col in first_row.keys():
        if first_row[col] and any(FIELDS[f] == first_row[col] for f in FIELDS.keys()):
            data.rename(columns={col: next(f for f in FIELDS if FIELDS[f] == first_row[col])}, inplace=True)
        else:
            del data[col]

    if dash.ctx.triggered_id == "excel_import_btn":
        data = data.to_dict('records')
    else:
        data = table_data + data.to_dict('records')
        if data[0] == {"": 1}:
            data = data[1:]
    return False, data


@dash.callback(
    [
        Output("card_modal", "is_open", allow_duplicate=True),
        Output("card_template_image_store", "data"),
        Output("card_preview_select", "options"),
        Output("card_preview_select", "value"),
    ],
    [
        Input("card_open_btn", "n_clicks"),
        Input("card_template_upload_btn", "contents"),
    ],
    [
        State("table", "data"),
        State("card_preview_select", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_card_modal(n_clicks, template, data, current):
    if template is None:
        path = "./static/card_template.png"
    else:
        path = f"{TEMP_FOLDER}/{random_string()}.png"
        base64_to_pil(template).save(path, format="PNG")

    return True, path, [{"label": "------", "value": "0"}] + [
        {"label": f"Id #{row['PlayerUniqueId']} {row['Lastname']} {row['Firstname']}", "value": row["PlayerUniqueId"]}
        for row in data if row.get("PlayerUniqueId")
    ], "0" if dash.ctx.triggered_id == "card_open_btn" else current


@dash.callback(
    Output("card_template_config", "data", allow_duplicate=True),
    Input("font_upload_btn", "contents"),
    State("font_upload_btn", "filename"),
    State("card_template_config", "data"),
    prevent_initial_call=True,
)
def upload_font(contents, filename, data):
    if not contents:
        raise PreventUpdate

    if not filename or not filename.lower().endswith(('.ttf', '.otf')):
        raise PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    font_path = os.path.join(FONTS_FOLDER, filename)
    with open(font_path, 'wb') as f:
        f.write(decoded)

    if data is None:
        data = {}

    data["config"]["font"] = font_path
    return data


clientside_callback(
    """
    function(data) {
        window.jsonEditor.update(data);
    }
    """,
    Input("card_template_config", "data"),
)


clientside_callback(
    """
    function(n_clicks) {
        if (!window.jsonEditor) {
            return;
        }
        const json = window.jsonEditor.get();
        console.log("JSON data:", json);
        return {
            content: JSON.stringify(json, null, 2),
            filename: "card_template_config.json"
        };
    }
    """,
    Output("download", "data", allow_duplicate=True),
    Input("card_template_export_config_btn", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(contents) {
        const base64Data = contents.split(',')[1];
        const jsonString = decodeURIComponent(Array.from(atob(base64Data)).map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join(''));
        const jsonObject = JSON.parse(jsonString);
        
        function mergeObject(obj, template) {
            obj = typeof obj === 'object' && obj !== null ? JSON.parse(JSON.stringify(obj)) : {};
            const result = {};
            for (const [key, value] of Object.entries(template)) {
                if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                    result[key] = mergeObject(obj[key] || {}, value);
                } else {
                    result[key] = obj.hasOwnProperty(key) ? obj[key] : value;
                }
            }
            return result;
        }
        
        const template = window.jsonEditor.get();
        const mergedJson = mergeObject(jsonObject, template);
        window.jsonEditor.update(mergedJson);
        
        return [
            null,
            mergedJson,
        ];
    }
    """,
    Output("card_template_import_config_btn", "contents"),
    Output('card_template_config', 'data', allow_duplicate=True),
    Input("card_template_import_config_btn", "contents"),
    prevent_initial_call=True,
)


clientside_callback(
    """
    function(n_clicks) {
        if (!window.jsonEditor) {
            return;
        }
        const json = window.jsonEditor.get();
        return json;
    }
    """,
    Output('card_template_config', 'data', allow_duplicate=True),
    Input('card_template_preview_update_btn', "n_clicks"),
    prevent_initial_call=True,
)


clientside_callback(
    """
    async function(n_clicks, data) {
        function waitForElm(selector) {
            return new Promise(resolve => {
                if (document.querySelector(selector)) {
                    return resolve(document.querySelector(selector));
                }
        
                const observer = new MutationObserver(mutations => {
                    if (document.querySelector(selector)) {
                        observer.disconnect();
                        resolve(document.querySelector(selector));
                    }
                });
        
                // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
            });
        }
    
        if (window.jsonEditor) {
            window.jsonEditor.destroy();
        }
        
        const container = await waitForElm("#jsoneditor");
        const initialJson = {
            "config": {
                "font": "",
                "scale": {
                    "width": 0,
                    "height": 0,
                },
                "dpi": {
                    "width": 72,
                    "height": 72,
                }
            },
            "name": {
                "anchor": "mm",
                "offsetX": 0,
                "offsetY": 0,
                "maxWidth": 500,
                "maxFontSize": 80,
                "maxWidthCompensate": 1,
                "offsetXCompensate": 1,
                "offsetYCompensate": 1,
                "color": "#000000",
                "template": "${Lastname} ${Firstname}",
                "groupId": "",
                "border": {
                    "strokeWeight": 0,
                    "color": "#000000",
                    "fill": "",
                    "radius": 0,
                    "padding": {
                        "top": 0,
                        "right": 0,
                        "bottom": 0,
                        "left": 0,
                    },
                    "minWidth": 0,
                    "minHeight": 0,
                },
            },
            "club": {
                "anchor": "mm",
                "offsetX": 0,
                "offsetY": 80,
                "maxWidth": 400,
                "maxFontSize": 30,
                "maxWidthCompensate": 1,
                "offsetXCompensate": 1,
                "offsetYCompensate": 1,
                "color": "#000000",
                "template": "${Club}",
                "groupId": "",
                "border": {
                    "strokeWeight": 0,
                    "color": "#000000",
                    "fill": "",
                    "radius": 0,
                    "padding": {
                        "top": 0,
                        "right": 0,
                        "bottom": 0,
                        "left": 0,
                    },
                    "minWidth": 0,
                    "minHeight": 0,
                },
            },
            "group": {
                "anchor": "mm",
                "offsetX": 0,
                "offsetY": 30,
                "maxWidth": 400,
                "maxFontSize": 30,
                "maxWidthCompensate": 1,
                "offsetXCompensate": 1,
                "offsetYCompensate": 1,
                "color": "#000000",
                "template": "Group: ${Group}",
                "groupId": "",
                "border": {
                    "strokeWeight": 0,
                    "color": "#000000",
                    "fill": "",
                    "radius": 0,
                    "padding": {
                        "top": 0,
                        "right": 0,
                        "bottom": 0,
                        "left": 0,
                    },
                    "minWidth": 0,
                    "minHeight": 0,
                },
            },
            "id": {
                "anchor": "mm",
                "offsetX": 100,
                "offsetY": 30,
                "maxWidth": 100,
                "maxFontSize": 30,
                "maxWidthCompensate": 1,
                "offsetXCompensate": 1,
                "offsetYCompensate": 1,
                "color": "#000000",
                "template": "${PlayerUniqueId}",
                "groupId": "",
                "border": {
                    "strokeWeight": 0,
                    "color": "#000000",
                    "fill": "",
                    "radius": 0,
                    "padding": {
                        "top": 0,
                        "right": 0,
                        "bottom": 0,
                        "left": 0,
                    },
                    "minWidth": 0,
                    "minHeight": 0,
                },
            },
        };
        
        const schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "font": { "type": "string" },
                        "scale": {
                            "type": "object",
                            "properties": {
                                "width": { "type": "number", "default": 0 },
                                "height": { "type": "number", "default": 0 },
                            },
                            "default": {
                                "width": 0,
                                "height": 0,
                            }
                        },
                        "dpi": {
                            "type": "object",
                            "properties": {
                                "width": { "type": "number", "default": 72 },
                                "height": { "type": "number", "default": 72 },
                            },
                            "default": {
                                "width": 72,
                                "height": 72,
                            }
                        }
                    },
                },
                "name": { "$ref": "#/definitions/labelBlock" },
                "club": { "$ref": "#/definitions/labelBlock" },
                "group": { "$ref": "#/definitions/labelBlock" },
                "id": { "$ref": "#/definitions/labelBlock" }
            },
            "definitions": {
                "labelBlock": {
                    "type": "object",
                    "properties": {
                        "anchor": {
                            "type": "string",
                            "enum": [
                                "mm", "ma", "mt", "ms", "mb", "md",
                                "lm", "la", "lt", "ls", "lb", "ld",
                                "rm", "ra", "rt", "rs", "rb", "rd",
                            ],
                        },
                    },
                }
            }
        }
        
        const options = {
            mode: "form",
            search: false,
            name: "Player Card Config",
            schema: schema,
            onNodeName: function ({ path, type, size, value }) {
                return ` `;
            }
        };
        const editor = new JSONEditor(container, options);
        editor.update(data || initialJson);
        window.jsonEditor = editor;  // Store the editor in a global variable for later use
        
        return editor.get();
    }
    """,
    Output("card_template_config", "data", allow_duplicate=True),
    Input("card_open_btn", "n_clicks"),
    State("card_template_config", "data"),
    prevent_initial_call=True,
)


def draw_text(img: Image, row: dict, row_config: dict, config: dict) -> Image:
    if not row:
        return img
    try:
        text = Template(row_config["template"]).render(**generate_name(row))
    except NameError:
        text = row_config["template"]
    if not text:
        return img
    text = unicodedata.normalize('NFC', text)

    img = img.copy()
    row_config = copy.deepcopy(row_config)
    d = ImageDraw.Draw(img)

    font_path = config["font"] if config.get("font", None) else "./Roboto.ttf"
    font_size = row_config["maxFontSize"]
    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        font_path = "./Roboto.ttf"
        font = ImageFont.truetype(font_path, font_size)
    while d.textlength(text, font) >= row_config["maxWidth"]:
        font_size -= 1
        row_config["maxWidth"] = row_config["maxWidth"] * row_config["maxWidthCompensate"]
        row_config["offsetX"] = row_config["offsetX"] * row_config["offsetXCompensate"]
        row_config["offsetY"] = row_config["offsetY"] * row_config["offsetYCompensate"]
        font = ImageFont.truetype(font_path, font_size)

    center = img.width // 2, img.height // 2
    center = (
        center[0] + row_config["offsetX"],
        center[1] + row_config["offsetY"]
    )

    if row_config["border"]["strokeWeight"] > 0:
        left, top, right, bottom = d.textbbox(center, text, font=font, anchor=row_config["anchor"])
        color = Template(row_config["border"]["color"]).render(**generate_name(row), **GLOBAL_CONTEXT)
        box = [
            left - row_config["border"]["padding"]["left"],
            top - row_config["border"]["padding"]["top"],
            right + row_config["border"]["padding"]["right"],
            bottom + row_config["border"]["padding"]["bottom"]
        ]

        if row_config["border"]["minWidth"] > 0 and (box[2] - box[0]) < row_config["border"]["minWidth"]:
            min_width = row_config["border"]["minWidth"]
            if row_config["anchor"][0] == "l":
                box[2] += min_width - (box[2] - box[0])
            elif row_config["anchor"][0] == "r":
                box[0] -= min_width - (box[2] - box[0])
            else:
                center_x = (box[0] + box[2]) // 2
                half_width = min_width // 2
                box[0] = center_x - half_width
                box[2] = center_x + (min_width - half_width)
        if row_config["border"]["minHeight"] > 0 and (box[3] - box[1]) < row_config["border"]["minHeight"]:
            min_height = row_config["border"]["minHeight"]
            if row_config["anchor"][1] == "t":
                box[3] += min_height - (box[3] - box[1])
            elif row_config["anchor"][1] == "b":
                box[1] -= min_height - (box[3] - box[1])
            else:
                center_y = (box[1] + box[3]) // 2
                half_height = min_height // 2
                box[1] = center_y - half_height
                box[3] = center_y + (min_height - half_height)

        d.rounded_rectangle(
            box,
            outline=color,
            width=row_config["border"]["strokeWeight"],
            fill=None if not row_config["border"]["fill"] else Template(row_config["border"]["fill"]).render(**generate_name(row), **GLOBAL_CONTEXT),
            radius=row_config["border"]["radius"]
        )

    try:
        d.text(center, text, fill=Template(row_config["color"]).render(**generate_name(row), **GLOBAL_CONTEXT), anchor=row_config["anchor"], font=font)
    except NameError:
        d.text(center, text, fill="#000000", anchor=row_config["anchor"], font=font)

    return img


@dash.callback(
    Output("card_preview_image", "src", allow_duplicate=True),
    Input("card_template_image_store", "data"),
    Input("card_template_config", "data"),
    Input("card_preview_select", "value"),
    State("table", "data"),
    prevent_initial_call=True,
)
def update_card_preview_image(template, config, preview, data):
    if not template:
        raise PreventUpdate
    if not config:
        image = Image.open(template).convert("RGBA")
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"

    image = Image.open(template).convert("RGBA")
    if config["config"]["scale"]["width"] > 0 and config["config"]["scale"]["height"] > 0:
        image = image.resize((config["config"]["scale"]["width"], config["config"]["scale"]["height"]))
    elif config["config"]["scale"]["width"] > 0:
        image.thumbnail((config["config"]["scale"]["width"], image.height))
    elif config["config"]["scale"]["height"] > 0:
        image.thumbnail((image.width, config["config"]["scale"]["height"]))
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    pattern = r'#(?:[A-Fa-f0-9]{3}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{8})\b'

    d = ImageDraw.Draw(image)
    if preview == "0":
        d.line(((0, image.height // 2), (image.width, image.height // 2)), "gray")
        d.line(((image.width // 2, 0), (image.width // 2, image.height)), "gray")

    d = ImageDraw.Draw(overlay)

    groups = {}
    if not config["config"].get("font", None):
        config["config"]["font"] = "./Roboto.ttf"
    for k, value in config.items():
        if k == "config":
            continue

        if preview == "0":
            center = image.width // 2, image.height // 2
            center = (
                center[0] + value["offsetX"],
                center[1] + value["offsetY"]
            )
            text = ""
            font = ImageFont.truetype(config["config"]["font"], value["maxFontSize"])
            while d.textlength(text, font) < value["maxWidth"]:
                text += "A"
            left, top, right, bottom = d.textbbox(center, text, font=font, anchor=value["anchor"])
            color = re.search(pattern, value["color"])
            d.rectangle(
                [left, top, right, bottom],
                fill=hex_to_rgb(color.group() if color else "#000000") + (128,),
                outline=hex_to_rgb(color.group() if color else "#000000")
            )
            if value.get("groupId", None):
                groups.setdefault(value["groupId"], []).append((left, top, right, bottom))
        else:
            row = next((r for r in data if r.get("PlayerUniqueId") == int(preview)), None)
            overlay = draw_text(overlay, row, value, config["config"])

    for group in groups.values():
        if preview != "0" or len(group) == 1:
            continue
        if len(group) > 1:
            left = min(x[0] for x in group)
            top = min(x[1] for x in group)
            right = max(x[2] for x in group)
            bottom = max(x[3] for x in group)
            d.rectangle(
                [left, top, right, bottom],
                outline="red",
                width=3
            )

    image = Image.alpha_composite(image, overlay).convert("RGB")
    image.thumbnail((1200, 1200))

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    result = f"data:image/jpeg;base64,{img_str}"

    return result


@dash.callback(
    Output("download", "data", allow_duplicate=True),
    Input("card_download_current_btn", "n_clicks"),
    Input("card_download_all_btn", "n_clicks"),
    State("card_template_image_store", "data"),
    State("card_template_config", "data"),
    State("table", "data"),
    State("card_preview_select", "value"),
    running=[
        (Output("card_download_current_btn", "disabled"), True, False),
        (Output("card_download_all_btn", "disabled"), True, False),
    ],
    prevent_initial_call=True,
)
def download_card(n_clicks_current, n_clicks_all, template, config, data, current):
    if not template or not config or not data:
        raise PreventUpdate

    image = Image.open(template).convert("RGBA")
    if config["config"]["scale"]["width"] > 0 and config["config"]["scale"]["height"] > 0:
        image = image.resize((config["config"]["scale"]["width"], config["config"]["scale"]["height"]))
    elif config["config"]["scale"]["width"] > 0:
        image.thumbnail((config["config"]["scale"]["width"], image.height))
    elif config["config"]["scale"]["height"] > 0:
        image.thumbnail((image.width, config["config"]["scale"]["height"]))
    if dash.ctx.triggered_id == "card_download_current_btn":
        if current == "0":
            raise PreventUpdate

        row = next((r for r in data if r.get("PlayerUniqueId") == int(current)), None)
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        for k, value in config.items():
            if k == "config":
                continue
            overlay = draw_text(overlay, row, value, config["config"])

        image = Image.alpha_composite(image, overlay)

        buffered = BytesIO()
        image.save(buffered, format="PNG", dpi=(config["config"]["dpi"]["width"], config["config"]["dpi"]["height"]))
        return dcc.send_bytes(
            buffered.getvalue(),
            filename=f"player_card_#{row['PlayerUniqueId']}.png"
        )
    else:
        images = []
        for row in data:
            overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
            for k, value in config.items():
                if k == "config":
                    continue
                overlay = draw_text(overlay, row, value, config["config"])

            result = Image.alpha_composite(image, overlay)

            buffered = BytesIO()
            result.save(buffered, format="PNG", dpi=(config["config"]["dpi"]["width"], config["config"]["dpi"]["height"]))
            images.append((buffered.getvalue(), f"player_card_#{row['PlayerUniqueId']}.png"))

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for img_data, filename in images:
                zip_file.writestr(filename, img_data)

        return dcc.send_bytes(
            zip_buffer.getvalue(),
            filename="player_cards.zip"
        )
