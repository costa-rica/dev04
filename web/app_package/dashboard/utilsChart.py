from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.io import curdoc
from bokeh.themes import built_in_themes, Theme
from bokeh.models import ColumnDataSource, Grid, LinearAxis, Plot, Text, Span
from datetime import datetime, timedelta
import os
from flask import current_app
from wsh_models import sess, Oura_sleep_descriptions, Weather_history, User_location_day
import pandas as pd
from flask_login import current_user
import json

def make_oura_df():
    # STEP 1: OURA
    #get all summary_dates and scores from oura
    USER_ID = current_user.id if current_user.id !=2 else 1

    base_query = sess.query(Oura_sleep_descriptions).filter_by(user_id = 1)
    df_oura = pd.read_sql(str(base_query)[:-1] + str(USER_ID), sess.bind)
    table_name = 'oura_sleep_descriptions_'
    cols = list(df_oura.columns)
    for col in cols: df_oura = df_oura.rename(columns=({col: col[len(table_name):]}))
        
    # if len(summary_dates) > 0:
    if len(df_oura) > 0:
    # - make df_oura = dates, scores
        df_oura_scores = df_oura[['id', 'summary_date', 'score']]
    #     Remove duplicates keeping the last entryget latest date
        df_oura_scores = df_oura_scores.drop_duplicates(subset='summary_date', keep='last')
        df_oura_scores.rename(columns=({'summary_date':'date'}), inplace= True)
        return df_oura_scores
    else:
        df_oura


def make_user_loc_day_df():
    USER_ID = current_user.id if current_user.id !=2 else 1
    users_loc_da_base = sess.query(User_location_day).filter_by(user_id=1)
    df_loc_da = pd.read_sql(str(users_loc_da_base)[:-1] + str(USER_ID), sess.bind)
    table_name = 'user_location_day_'
    cols = list(df_loc_da.columns)
    for col in cols: df_loc_da = df_loc_da.rename(columns=({col: col[len(table_name):]}))
    df_loc_da = df_loc_da[['id', 'date', 'location_id']]
    df_loc_da = df_loc_da.drop_duplicates(subset='date', keep='last')
    return df_loc_da

def make_weather_hist_df():
    weather_base = sess.query(Weather_history)
    df_weath_hist = pd.read_sql(str(weather_base), sess.bind)
    table_name = 'weather_history_'
    cols = list(df_weath_hist.columns)
    for col in cols: df_weath_hist = df_weath_hist.rename(columns=({col: col[len(table_name):]}))
    df_weath_hist = df_weath_hist[['datetime','temp','location_id', 'cloudcover']]
    df_weath_hist = df_weath_hist.rename(columns=({'datetime': 'date'}))
    return df_weath_hist



# def make_chart(dates_list, temp_data_list, sleep_data_list):
def make_chart(lists_tuple, buttons_dict):
    dates_list, sleep_data_list, temp_data_list, cloud_list = lists_tuple

    date_start = max(dates_list) - timedelta(days=8.5)
    date_end = max(dates_list) + timedelta(days=1)
    print('waht is hte last date:', dates_list[-1])
    fig1=figure(toolbar_location=None,tools='xwheel_zoom,xpan',active_scroll='xwheel_zoom',
            x_range=(date_start,date_end),
            y_range=(-10,110),sizing_mode='stretch_width', height=400)


    if temp_data_list != 'is empty':
        print('** STEP 2:  temp NOT empty ')
#Temperature
        if buttons_dict.get('avg_temp') !=1:
            fig1.circle(dates_list,temp_data_list, 
                legend_label="Temperature (F)", 
                fill_color='#c77711', 
                line_color=None,
                size=20)

            source1 = ColumnDataSource(dict(x=dates_list, y=temp_data_list, text=temp_data_list)) # data
            glyph1 = Text(text="text",text_font_size={'value': '10px'},x_offset=-5, y_offset=5) # Image
            fig1.add_glyph(source1, glyph1)

#cloud cover
        if buttons_dict.get('cloudiness') !=1:
            fig1.circle(dates_list,cloud_list, 
                legend_label="Cloudcover", 
                fill_color='#6cacc3', 
                line_color="#3288bd",
                size=20, line_width=3)

            source1_cloud = ColumnDataSource(dict(x=dates_list, y=cloud_list, text=cloud_list)) # data
            glyph1_cloud = Text(text="text",text_font_size={'value': '10px'},x_offset=-5, y_offset=5) # Image
            fig1.add_glyph(source1_cloud, glyph1_cloud)

#sleep rectangle label
    if sleep_data_list != 'is empty':
        fig1.square(dates_list, sleep_data_list, legend_label = 'Oura Sleep Score', size=20, color="olive", alpha=0.5)
        
        source4 = ColumnDataSource(dict(x=dates_list, y=sleep_data_list,
            text=sleep_data_list))
        glyph4 = Text(text="text",text_font_size={'value': '10px'},x_offset=-5, y_offset=5)
        fig1.add_glyph(source4, glyph4)

    fig1.ygrid.grid_line_color = None
    fig1.yaxis.major_label_text_color = None
    fig1.yaxis.major_tick_line_color = None
    fig1.yaxis.minor_tick_line_color = None

    fig1.legend.background_fill_color = "#578582"
    fig1.legend.background_fill_alpha = 0.2
    fig1.legend.border_line_color = None
    theme_1=curdoc().theme = Theme(filename=os.path.join(current_app.static_folder, 'chart_theme_2.yml'))

    script1, div1 = components(fig1, theme=theme_1)

    cdn_js=CDN.js_files

    return script1, div1, cdn_js



def buttons_dict_util(formDict, dashboard_routes_dir, buttons_dict):
    # if len(formDict)>0:
    #1 read json dict with switches
    if os.path.exists(os.path.join(dashboard_routes_dir,'buttons_dict.json')):
        with open(os.path.join(dashboard_routes_dir,'buttons_dict.json')) as json_file:
            buttons_dict = json.load(json_file)

    if buttons_dict.get(list(formDict.keys())[0]) != None:
        buttons_dict[list(formDict.keys())[0]] = (buttons_dict.get(list(formDict.keys())[0]) + int(formDict[list(formDict.keys())[0]])) % 2
    else:
        buttons_dict[list(formDict.keys())[0]] = int(formDict[list(formDict.keys())[0]])

    with open(os.path.join(dashboard_routes_dir,'buttons_dict.json'), 'w') as convert_file:
        convert_file.write(json.dumps(buttons_dict))
    print('Wrote buttons_dict.json')
    return buttons_dict