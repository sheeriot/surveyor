from django import template
# from icecream import ic
import pandas as pd
from django.urls import reverse

register = template.Library()


def convert_data_frame_to_html_table_headers(df):
    html = "<tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr>"
    return html


def convert_data_frame_to_html_table_rows(df):
    html = ""
    for row in df.values:
        row_html = "<tr>"
        for value in row:
            if isinstance(value, pd.Timestamp):
                row_html += f"<td>{value.strftime('%Y-%m-%d %H:%M:%S(%Z)')}</td>"
            else:
                row_html += f"<td>{value}</td>"
        row_html += "</tr>"
        html += row_html
    return html


# def convert_data_frame_to_html_table_rows(df):
def dataframe_to_htmltablerows_withlinks(df):
    html = ""
    for index, row in df.iterrows():
        row_html = "<tr>"
        for col in df.columns:
            row_html += "<td>"
            value = row[col]
            if isinstance(value, pd.Timestamp):
                row_html += f"{ value.strftime('%Y-%m-%d %H:%M:%S(%Z)') }"
            elif col.lower() in {'device', 'deveui', 'dev_eui'}:
                row_html += f"<strong><a href='/device/{ value }/'>{ value }</a></strong>"
            else:
                row_html += f"{ value }"
            row_html += "</td>"
        row_html += "</tr>"
        html += row_html
    return html


# def convert_data_frame_to_html_table_rows(df):
@register.simple_tag
def dataframe_to_htmltablerows_withlinks2(df, source_id, meas, start_mark, end_mark):
    html = ""
    for index, row in df.iterrows():
        # start a new row
        row_html = "<tr>"
        for col in df.columns:
            row_html += "<td>"
            value = row[col]
            if isinstance(value, pd.Timestamp):
                row_html += f"{ value.strftime('%Y-%m-%d %H:%M:%S(%Z)') }"
            elif col.lower() in {'device', 'deveui', 'dev_eui'}:
                url = reverse('bucketdevice_withtimes', args=[source_id, meas, value, start_mark, end_mark])
                row_html += f"<strong><a href='{ url }' target='_blank'>{ value }</a></strong>"
            else:
                row_html += f"{ value }"
            row_html += "</td>"
        row_html += "</tr>"
        # add row to table html
        html += row_html
    return html


register.filter("convert_data_frame_to_html_table_rows", convert_data_frame_to_html_table_rows)
register.filter("convert_data_frame_to_html_table_headers", convert_data_frame_to_html_table_headers)
register.filter("dataframe_to_htmltablerows_withlinks", dataframe_to_htmltablerows_withlinks)
# register.filter("dataframe_to_htmltablerows_withlinks2", dataframe_to_htmltablerows_withlinks2)
