import dash
from dash import Output, Input


def table(id, **kwargs):
    default_kwargs = dict(
        id=id,
        editable=True,
        filter_action="none",
        sort_action="none",
        column_selectable=False,
        row_selectable=False,
        row_deletable=True,
        page_current=0,
        page_size=999,
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
        style_header_conditional=[
            {
                "if": {"column_editable": False},
                "color": "rgba(0, 0, 0, 0.5)",
            }
        ],
        style_data_conditional=[
            {
                "if": {"state": "active"},
                "textAlign": "left",
            }, {
                "if": {"column_editable": False},
                "opacity": 0.7,
            }
        ],
        style_table={
            "overflow": "scroll",
        },
    )

    @dash.callback(
        Output(id, "row_deletable"),
        Input(id, "data"),
    )
    def row_deletable(data):
        return len(data) > 1

    return dash.dash_table.DataTable(
        **(default_kwargs | kwargs)
    )
