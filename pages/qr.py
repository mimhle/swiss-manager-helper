import base64
import re
from io import BytesIO

import dash
import dash_bootstrap_components as dbc
import numpy
import plotly.express as px
import qrcode
from dash import Output, Input, ALL, State, dcc
from dash.exceptions import PreventUpdate

dash.register_page(
    __name__,
    path='/qr',
)

layout = dbc.Container([
    dbc.Container([
        dbc.FormFloating([
            dbc.Textarea(id="input_qr", placeholder="Text to generate"),
            dbc.Label("Text to generate"),
        ]),
        dbc.Row([
            dbc.Container([
                dbc.FormFloating([
                    dbc.Input(id="size_qr", type="number", value=0, min=0, max=40),
                    dbc.Label("QR version (size, 0 for auto)"),
                ], className="w-fit"),
            ], className="w-fit m-0"),
            dbc.Container([
                dbc.FormFloating([
                    dbc.Input(id="box_size_qr", type="number", value=20, min=0),
                    dbc.Label("Box size (px)"),
                ], className="w-fit m-0"),
            ], className="w-fit m-0"),
            dbc.Container([
                dbc.FormFloating([
                    dbc.Input(id="border_qr", type="number", value=1, min=0),
                    dbc.Label("Border size (box size unit)"),
                ], className="w-fit m-0"),
            ], className="w-fit m-0"),
            dbc.Container([
                dbc.Row([
                    dbc.Label("Fill color", className="m-0 w-fit pl-0 text-sm text-gray-500"),
                    dbc.Input(id="fill_color_qr", type="color", value="#000000", className="w-24 h-6"),
                ], className="w-fit m-0"),
                dbc.Checklist(
                    options=[
                        {"label": "Transparent", "value": 1, "disabled": True},  # fill color does not support transparency
                    ],
                    value=[],
                    id="fill_color_transparent_qr",
                    className="w-fit text-sm",
                ),
            ], className="w-fit m-0 border-[1px] border-gray-250 rounded-md p-1 px-3"),
            dbc.Container([
                dbc.Row([
                    dbc.Label("Back color", className="m-0 w-fit pl-0 text-sm text-gray-500"),
                    dbc.Input(id="back_color_qr", type="color", value="#FFFFFF", className="w-24 h-6"),
                ], className="w-fit m-0"),
                dbc.Checklist(
                    options=[
                        {"label": "Transparent", "value": 1},
                    ],
                    value=[],
                    id="back_color_transparent_qr",
                    className="w-fit text-sm",
                ),
            ], className="w-fit m-0 border-[1px] border-gray-250 rounded-md p-1 px-3"),
        ], className="flex flex-row gap-1 mt-2 justify-start"),
    ], className="w-full flex flex-col gap-2"),
    dbc.Row([
        dbc.Button("Generate", id="generate_qr", className="me-1 w-fit"),
        dbc.Button("Download", color="info", id="download_btn_qr", className="w-fit", disabled=True),
        dbc.Button("Raw", color="info", id="raw_qr", className="w-fit", disabled=True),
    ], className="flex flex-row gap-2 mt-2"),
    dcc.Download(id="download_qr"),
    dbc.Container([], className="w-full", id="qr"),
    dcc.Location(id="url_qr"),
])


@dash.callback(
    Output("qr", "children"),
    Input("generate_qr", "n_clicks"),
    State("input_qr", "value"),
    State("size_qr", "value"),
    State("box_size_qr", "value"),
    State("border_qr", "value"),
    State("fill_color_qr", "value"),
    State("back_color_qr", "value"),
    State("fill_color_transparent_qr", "value"),
    State("back_color_transparent_qr", "value"),
)
def generate(
        n_clicks,
        input_qr,
        input_qr_size,
        input_box_size,
        input_border_size,
        input_fill_color,
        input_back_color,
        input_fill_color_transparent,
        input_back_color_transparent,
):
    if n_clicks is None:
        raise PreventUpdate

    # test
    qr = qrcode.QRCode(
        version=input_qr_size if input_qr_size and (input_qr_size > 0) else None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=input_box_size if input_box_size and (input_box_size > 0) else 20,
        border=input_border_size if input_border_size and (input_border_size > 0) else 0,
    )
    qr.add_data(input_qr)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color=(input_fill_color if input_fill_color else "black") if not input_fill_color_transparent else "transparent",
        back_color=(input_back_color if input_back_color else "white") if not input_back_color_transparent else "transparent",
    ).convert("RGBA")

    fig = px.imshow(
        numpy.array(img),
        binary_format="png",
        labels=dict(x="px", y="px"),
    )

    return [
        dcc.Graph(
            figure=fig,
            className="w-full inline-block",
            id={"type": "qr_container", "index": "qr_img"},
        ),
    ]


@dash.callback(
    Output("back_color_qr", "disabled"),
    Output("fill_color_qr", "disabled"),
    Input("back_color_transparent_qr", "value"),
    Input("fill_color_transparent_qr", "value"),
)
def toggle_transparent(back_color_transparent, fill_color_transparent):
    return bool(back_color_transparent), bool(fill_color_transparent)


@dash.callback(
    Output("download_btn_qr", "disabled"),
    Output("raw_qr", "disabled"),
    Output("raw_qr", "href"),
    Input({'type': 'qr_container', 'index': ALL}, "figure"),
)
def enable_buttons(fig):
    if not fig:
        raise PreventUpdate

    return False, False, fig[0]["data"][0]["source"]


@dash.callback(
    Output("download_qr", "data"),
    Input("download_btn_qr", "n_clicks"),
    State({'type': 'qr_container', 'index': ALL}, "figure"),
)
def download_qr(n_clicks, fig):
    if n_clicks is None:
        raise PreventUpdate

    img = re.sub('^data:image/.+;base64,', '', fig[0]["data"][0]["source"])

    return dcc.send_bytes(
        BytesIO(base64.b64decode(img)).getvalue(),
        filename="qr.png",
    )
