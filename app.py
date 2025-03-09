import re

import dash
import pandas as pd
import unicodedata
from dash import Dash, dash_table, dcc, html, Input, Output, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import xml.etree.ElementTree as ET
import xml.dom.minidom

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

app = Dash(
    __name__,
    external_scripts=['https://cdn.tailwindcss.com'],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

app.layout = dbc.Container([
    dbc.Tabs(
        [
            dbc.Tab(label="Generate xml", tab_id="xml", children=[
                dbc.Container([
                    dbc.Button("Clear", color="secondary", disabled=True, className="w-fit", id="clear_column"),
                    dash_table.DataTable(
                        id="table",
                        columns=[
                            {
                                "name": v,
                                "id": k,
                                "deletable": False,
                                "selectable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
                                "type": "text",
                                "editable": k != "PlayerUniqueId" and k != "Lastname" and k != "Firstname",
                            } for k, v in FIELDS.items()
                        ],
                        data=df.to_dict('records'),
                        editable=True,
                        filter_action="none",
                        sort_action="none",
                        column_selectable="single",
                        row_selectable=False,
                        row_deletable=True,
                        page_current=0,
                        page_size=999,
                        persistence=True,
                        persisted_props=['data'],
                        persistence_type='local',
                        css=[{
                            "selector": ".column-header-name",
                            "rule": "padding: 0 0.25rem"
                        }, {
                            "selector": ".input-active",
                            "rule": "text-align: left !important"
                        }],
                        style_cell={'textAlign': 'left'},
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold",
                            "padding": "10px 0px",
                        },
                        style_data_conditional=[
                            {
                                "if": {"state": "active"},
                                "textAlign": "left",
                            }, {
                                "if": {"column_editable": False},
                                "opacity": 0.7,
                            }
                        ],
                    ),
                    dbc.Button("Generate", color="primary", className="me-1 w-fit", id="generate"),
                    dcc.Download(id="download-text"),
                ], className="flex flex-col gap-2 p-0")
            ]),
            dbc.Tab(label="Normalize", tab_id="normalize", children=[
                dbc.Row(
                    [
                        dbc.Button("Click me", color="primary"),
                    ]
                ),
            ]),
        ],
        id="tabs",
        active_tab="xml",
    ), dbc.Spinner(
        [
            dcc.Store(id="store"),
            html.Div(id="tab-content", className=""),
        ],
        delay_show=100,
    ),
], className="flex flex-col gap-2 my-2")


@app.callback(
    Output("table", "row_deletable"),
    Input("table", "data"),
)
def row_deletable(data):
    return len(data) > 1


@app.callback(
    Output("table", "data", allow_duplicate=True),
    Input("table", "data"),
    prevent_initial_call=True,
)
def change_data(data):
    if not data:
        raise PreventUpdate

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

    if not data:
        data = [{"": 1}]

    return data


@app.callback(
    Output("clear_column", "disabled"),
    Input("table", "derived_viewport_selected_columns"),
)
def clear_column(selected_col):
    return not selected_col


@app.callback(
    Output("table", "data", allow_duplicate=True),
    Output("table", "selected_columns"),
    Input("clear_column", "n_clicks"),
    Input("table", "derived_viewport_selected_columns"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def clear_column(n_clicks, selected_col, data):
    if not selected_col:
        raise PreventUpdate

    if dash.ctx.triggered_id == "clear_column":
        for col in selected_col:
            for row in data:
                row[col] = ""

        return data, []

    raise PreventUpdate


@app.callback(
    Output("download-text", "data"),
    Input("generate", "n_clicks"),
    Input("table", "data"),
    prevent_initial_call=True,
)
def download_text(n_clicks, data):
    if dash.ctx.triggered_id != "generate":
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


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
