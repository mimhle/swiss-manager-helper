import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output
from dash_extensions.enrich import DashProxy

app = DashProxy(
    __name__,
    external_scripts=['https://cdn.tailwindcss.com'],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
)

app.layout = dbc.Container([
    dbc.Tabs(
        [
            dbc.Tab(label="Generate xml", tab_id="xml"),
            dbc.Tab(label="Normalize", tab_id="normalize"),
        ],
        id="tabs",
        active_tab="xml",
    ), dbc.Spinner(
        [
            dcc.Location(id="url"),
            html.Div(id="hidden_div_for_redirect_callback"),
            html.Div(id="tab-content", className=""),
            dash.page_container
        ],
        delay_show=300,
    ),
], className="flex flex-col gap-2 my-2")


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
