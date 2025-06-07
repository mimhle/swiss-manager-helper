import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from dash_extensions.enrich import DashProxy

app = DashProxy(
    __name__,
    external_scripts=['https://cdn.tailwindcss.com', 'https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.1.3/jsoneditor.min.js'],
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, 'https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.1.3/jsoneditor.min.css'],
    use_pages=True,
)

server = app.server

app.layout = dbc.Container([dbc.Container([
    dbc.Row([
        html.H1("Swiss-Manager Helper", className="text-3xl font-bold mb-3 w-fit"),
        html.A(html.I(className="bi bi-link-45deg"), href="https://swiss-manager.at/", className="m-0 p-0 w-fit", target="_blank", title="Swiss Manager official website"),
    ]),
    dbc.Tabs(
        [
            dbc.Tab(label=" Generate xml", tab_id="xml", labelClassName="bi bi-filetype-xml"),
            # dbc.Tab(label="Normalize", tab_id="normalize"),
            dbc.Tab(label=" Summarize team result", tab_id="summarize", labelClassName="bi bi-bar-chart-line"),
            dbc.Tab(label=" QR code generator", tab_id="qr", labelClassName="bi bi-qr-code")
        ],
        id="tabs",
        active_tab="xml",
        className="h-fit",
    ), dbc.Spinner(
        [
            dcc.Location(id="url"),
            html.Div(id="hidden_div_for_redirect_callback"),
            html.Div(id="tab-content", className=""),
            dash.page_container
        ],
        delay_show=300,
        fullscreen=True,
    ),
], className="flex flex-col item-center gap-2 m-0 mx-auto py-2 pb-5 min-h-screen w-screen"),
    dbc.Container(
        html.A(dbc.Row([
            "Developed by mimhle",
            html.Img(src="/static/github.png", className="w-5 h-5 ml-1 my-auto p-0"),
        ], className="w-fit p-1 px-2 text-sm text-gray-500"
        ), href="https://github.com/mimhle/swiss-manager-helper", className="block w-fit ml-auto", target="_blank", title="GitHub repository"),
        className="absolute bottom-0 right-0 w-screen no-max-width border-t-[1px] border-gray-300"
    ),
], className="relative no-max-width h-fit overflow-scroll"),


@app.callback(
    Output("hidden_div_for_redirect_callback", "children"),
    Input("tabs", "active_tab")
)
def render_content(tab):
    return dcc.Location(pathname=f"/{tab}", id="")


@app.callback(
    Output("tabs", "active_tab"),
    Input("url", "pathname")
)
def render_content(pathname):
    if pathname == "/":
        return "xml"
    return pathname.split("/")[-1]


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
