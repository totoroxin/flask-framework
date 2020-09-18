import pandas as pd

from flask import Flask, render_template, request, redirect
from alpha_vantage.timeseries import TimeSeries
from bokeh.embed import components
from bokeh.layouts import gridplot, column
from bokeh.plotting import figure, output_file, show, ColumnDataSource

from bokeh.models.widgets import Dropdown
from bokeh.io import curdoc
from bokeh.models import BooleanFilter, CDSView, Select, Range1d, HoverTool
from bokeh.palettes import Category20
from bokeh.models.formatters import NumeralTickFormatter

# import bokeh
# bokeh.__version__

app = Flask(__name__)
app.vars = {}

# Define constants
W_PLOT = 900
H_PLOT = 600
TOOLS = 'pan,wheel_zoom,box_zoom,hover,reset,save'

VBAR_WIDTH = 0.2
RED = Category20[7][6]
GREEN = Category20[5][4]

BLUE = Category20[3][0]
BLUE_LIGHT = Category20[3][1]

ORANGE = Category20[3][2]
PURPLE = Category20[9][8]
BROWN = Category20[11][10]


# connect to alpha vantage API
key = open('API_key.txt')
ts = TimeSeries(key=key.readline(), output_format='pandas', indexing_type='date')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/graph', methods=['POST'])
def graph():
    form_data = request.form
    ticker = form_data.get('ticker')
    if ticker is None or ticker == '':
        return redirect('/error')
    features = form_data.getlist('features')
    
    # read data
    df = read_stock_price(ticker)
    
    # line chart
    p_stock_line = plot_stock_price_line(df, ticker, features)
    script_line, div_line = components(p_stock_line)
    
    # bar chart
    p_stock_bar = plot_stock_price_bar(df, ticker, features)
    script_bar, div_bar = components(p_stock_bar)
    
    return render_template(
        'graph.html', 
        bokeh_script_line=script_line,
        bokeh_div_line=div_line,
        bokeh_script_bar=script_bar,
        bokeh_div_bar=div_bar,
        ticker=ticker,
        features=features
    )


def read_stock_price(ticker):
    data, meta_data = ts.get_daily_adjusted(symbol=ticker, outputsize='full')
    data = data.reset_index()
    data = data.rename(columns={
        'date': 'Date',
        '1. open': 'Open',
        '2. high': 'High',
        '3. low': 'Low',
        '4. close': 'Close',
        '5. adjusted close': 'Adjusted Close',
        '6. volume': 'Volume',
        '7. dividend amount': 'Dividend',
        '8. split coefficient': 'Coefficient'
    })
    data = data[data['Date'] > '2019-01-01']
    return data

def plot_stock_price_line(df, ticker, features):
    p = figure(
        plot_width=W_PLOT, 
        plot_height=H_PLOT,
        tools=TOOLS,
        title = f'Alpha-Vantage Real-Time Stock Price - Line Chart - {ticker}',
        x_axis_type='datetime',
        x_axis_label='date',
        y_axis_label='price'
    )
    
    feature_colors = {'Open':'lightskyblue','High':'green','Low':'indianred','Close':'gold'}
    for feature in features:
        p.line(df['Date'], df[feature], color=feature_colors[feature], legend=feature)
    
    p.grid.grid_line_alpha = 0.3
    p.legend.location = 'top_right'
    
    return p

def plot_stock_price_bar(df, ticker, features):
    df = df.sort_values(by=['Date'])
    stock = ColumnDataSource(df)
    
    p = figure(
        plot_width=W_PLOT, 
        plot_height=H_PLOT,
        tools=TOOLS,
        title = f'Alpha-Vantage Real-Time Stock Price - Bar Chart - {ticker}',
        x_axis_label='date',
        y_axis_label='price'
    )
    p.grid.grid_line_alpha = 0.3

    inc = stock.data['Close'] > stock.data['Open']
    dec = stock.data['Open'] > stock.data['Close']
    view_inc = CDSView(source=stock, filters=[BooleanFilter(inc)])
    view_dec = CDSView(source=stock, filters=[BooleanFilter(dec)])

    p.segment(x0='index', x1='index', y0='Low', y1='High', color=RED, source=stock, view=view_inc)
    p.segment(x0='index', x1='index', y0='Low', y1='High', color=GREEN, source=stock, view=view_dec)

    p.vbar(x='index', width=VBAR_WIDTH, top='Open', bottom='Close', fill_color=BLUE, line_color=BLUE,
           source=stock,view=view_inc, name="price")
    p.vbar(x='index', width=VBAR_WIDTH, top='Open', bottom='Close', fill_color=RED, line_color=RED,
           source=stock,view=view_dec, name="price")
    
    # map dataframe indices to date strings and use as label overrides
    p.xaxis.major_label_overrides = {
        i+int(stock.data['index'][0]): date.strftime('%b %d') for i, date in enumerate(pd.to_datetime(stock.data["Date"]))
    }
    p.xaxis.bounds = (stock.data['index'][0], stock.data['index'][-1])

    # Add more ticks in the plot
    p.x_range.range_padding = 0.05
    p.xaxis[0].ticker.desired_num_ticks = 40  # ticker is not the same stock ticker but a bokeh axis term
    p.xaxis.major_label_orientation = 3.14/4
    
    # Select specific tool for the plot
    price_hover = p.select(dict(type=HoverTool))

    # Choose, which glyphs are active by glyph name
    price_hover.names = ['price']
    # Creating tooltips
    price_hover.tooltips = [('Datetime', '@Date{%Y-%m-%d}'),
                            ('Open', '@Open{$0,0.00}'),
                            ('Close', '@Close{$0,0.00}'),
                            ('Volume', '@Volume{($ 0.00 a)}')]
    price_hover.formatters={'Date': 'datetime'}

    return p

@app.route('/error')
def error_request():
    return render_template('error_request.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)

    