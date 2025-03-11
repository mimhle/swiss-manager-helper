import dash
import dash_bootstrap_components as dbc
import pandas as pd
import unicodedata
from dash import Output, Input, ALL
from dash.exceptions import PreventUpdate

df = pd.DataFrame({
    "": [1],
})

dash.register_page(
    __name__,
    path='/normalize',
)

layout = dbc.Container([

])