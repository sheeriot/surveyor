from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

import dateutil.parser
import dateutil.tz
from time import perf_counter

import pandas as pd
# from icecream import ic

import folium

from accounts.models import Person
from surveyor.utils import init_datetime
from surveyor.settings import TIME_ZONE
from device.models import EndNode
from performer.colorscales import color_lookup_red0, color_lookup_green0
from surveyor.tower import tower_svg

from ..getGeowanData import getGeowanFrames
from ..geoWanFun import geowanSummFrames

from ..form_geoview import geoViewSelect


@login_required
def geoView(request, deveui='', **kwargs):
    username = request.user
    person = Person.objects.get(username=username)
    orgs_list = person.orgs_list()

    if timezone.get_current_timezone():
        tz = str(timezone.get_current_timezone())
    else:
        tz = TIME_ZONE
    zulu_tz = dateutil.tz.gettz('UTC')
    local_tz = dateutil.tz.gettz(tz)

    console_messages = []
    console_messages.append(F'Local Timezone: {tz}')

    if request.method == 'GET' and 'submit' in request.GET:
        form = geoViewSelect(request.GET, orgs_list=orgs_list)
        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            endnode = form.cleaned_data["endnode"]
            dev_eui = endnode.dev_eui.lower()
            source = endnode.influx_source
            meas = endnode.influx_measurement

        else:
            # form validation failed. Provide messages
            console_messages.append(F'Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
            }
            return render(request, 'geowan/geoView.html', context)

    elif request.method == 'GET' and kwargs:
        if 'start_mark' in kwargs:
            start_mark = kwargs.pop('start_mark')
            start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
            start = start_zulu.astimezone(local_tz)
        if 'end_mark' in kwargs:
            end_mark = kwargs.pop('end_mark')
            end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
            end = end_zulu.astimezone(local_tz)
        if 'endnode_id' in kwargs:
            endnode_id = kwargs.pop('endnode_id')
            endnode = EndNode.objects.get(pk=endnode_id)

        form = geoViewSelect({
            "endnode": endnode_id,
            "start": start,
            'end': end},
            orgs_list=orgs_list
        )

        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            endnode_id = form.cleaned_data["endnode"].id
            endnode = EndNode.objects.get(pk=endnode_id)
            dev_eui = endnode.dev_eui.lower()
            source = endnode.influx_source
            meas = endnode.influx_measurement
        else:
            # form validation failed. Provide messages
            console_messages.append(F'Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
                }
            return render(request, 'geowan/geoView.html', context)

    elif request.method == 'GET':

        yesterday_morning, now = init_datetime(tz)
        form = geoViewSelect(
            initial={
                'start': yesterday_morning,
                'end': now},
            orgs_list=orgs_list
        )
        context = {
            'form': form,
            'console_messages': console_messages,
            'results_display': False,
        }
        return render(request, 'geowan/geoView.html', context)

    # ------ being here means we have a valid form ------
    start_mark = start.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
    end_mark = end.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')

    context = {
        'form': form,
        'start': start,
        'start_mark': start_mark,
        'end': end,
        'end_mark': end_mark,
        'dev_eui': dev_eui,
        'endnode': endnode,
        'source': source,
        'source_id': source.id,
        'meas': meas,
    }

    start_timer = perf_counter()
    try:
        frames_df = getGeowanFrames(source.id, meas, dev_eui, start_zulu, end_zulu)
    except ValueError as err:
        console_messages.append(F'Cannot getGeoData: {err}')
        error_message = F'Cannot getGeoData: {err}'
        context['results_display'] = False
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'geowan/geoView.html', context)

    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    console_messages.append(F'Source Query Time: {query_time}')

    if frames_df.empty:
        context['results_display'] = False
        error_message = 'No data found'
        console_messages.append(error_message)
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'geowan/geoView.html', context)

    context['results_display'] = True

    context['frames_first'] = frames_df['time'].min()
    context['frames_last'] = frames_df['time'].max()

    # Summarize the frames into device_uplinks_df
    frames_df, uplinks_df = geowanSummFrames(frames_df)

    context['gps_uplinks'] = uplinks_df.shape[0]

    # Summarize the Gateway Location Table
    context['gateway_count'] = frames_df.gateway.nunique()
    if 'gw_lat' in frames_df.columns and 'gw_long' in frames_df.columns:
        gw_loc_df = frames_df[['gateway', 'gw_lat', 'gw_long']].dropna().drop_duplicates(subset=['gateway'])
        gw_loc_df = gw_loc_df.set_index('gateway')
        # frames_df = frames_df.drop(columns=['gw_latitude','gw_longitude'])
    else:
        console_messages.append('No gateway locations found')
        gw_loc_df = pd.DataFrame()
    context['gateway_loc_df'] = gw_loc_df.copy()

    # Localize the time for views and pass on frames an uplinks dataframes
    frames_df['time'] = frames_df['time'].dt.tz_convert(local_tz)
    context['frames_df'] = frames_df.copy()
    uplinks_df['time'] = uplinks_df['time'].dt.tz_convert(local_tz)
    context['uplinks_df'] = uplinks_df.copy()

    # =========
    # Maps the Data
    tower_icon = tower_svg()
    lat_center = round(uplinks_df['lat'].mean(), 5)
    long_center = round(uplinks_df['long'].mean(), 5)

    start_timer = perf_counter()

    map_one = folium.Map(
        location=(lat_center, long_center),
        zoom_start=14,
        scrollWheelZoom=False,
        control_scale=True,
        tiles="cartodbpositron",
    )

    # color the map markers
    # rssi_mean
    rssiscale_lower = -115
    rssiscale_upper = -85
    rssiscale_range = rssiscale_upper - rssiscale_lower
    # color the RSSI markers (rssi and rssi_c) on uplinks and on frames
    uplinks_df['rssi_color'] = uplinks_df['rssi'].apply(
            lambda x: color_lookup_red0((x - rssiscale_lower) / rssiscale_range * 100))
    uplinks_df['rssi_c_color'] = uplinks_df['rssi_c'].apply(
            lambda x: color_lookup_red0((x - rssiscale_lower) / rssiscale_range * 100))
    # frames markers
    frames_df['rssi_color'] = frames_df['rssi'].apply(
            lambda x: color_lookup_red0((x - rssiscale_lower) / rssiscale_range * 100))
    frames_df['rssi_c_color'] = frames_df['rssi_c'].apply(
            lambda x: color_lookup_red0((x - rssiscale_lower) / rssiscale_range * 100))

    snrscale_lower = -10
    snrscale_upper = 10
    snrscale_range = snrscale_upper - snrscale_lower
    # color the SNR markers on upinks_df and on frames_df
    uplinks_df['snr_color'] = uplinks_df['snr'].apply(
        lambda x: color_lookup_green0((x - snrscale_lower) / snrscale_range * 100))
    # frames markers
    frames_df['snr_color'] = frames_df['snr'].apply(
        lambda x: color_lookup_red0((x - snrscale_lower) / snrscale_range * 100))

    tower_markers = folium.FeatureGroup("Towers")
    for gateway, frame_stats in frames_df.groupby('gateway', observed=True):
        gw_loc = True
        try:
            gw_lat, gw_long = gw_loc_df.loc[gateway, ['gw_lat', 'gw_long']]
        except KeyError:
            gw_lat, gw_long = None, None
            gw_loc = False
        frame_stats = frame_stats.reset_index()

        # first the RSSI markers
        rssi_gw_group = folium.FeatureGroup(F"{gateway} - RSSI")

        # first the RSSI markers
        for index, row in frame_stats.iterrows():
            rssi_gw_group.add_child(folium.CircleMarker(
                location=(row['lat'], row['long']),
                radius=10,
                popup=f"""
                    GW:{ row['gateway'] }<br>
                    Count:{ row['count'] }<br>
                    RSSI:<strong>{row['rssi']}</strong>,
                    SNR:{row['snr']}<br>
                    Distance:{row['dist']:.2f}km<br>
                    { row['time'].strftime('%Y-%m-%d %H:%M(%Z)') }
                """,
                color=row['rssi_color'],
                # fill=False,
                fill_color=row['rssi_color'],
                fill_opacity=0.2,
            ))
            if gw_loc:
                # rssi_gw_group.add_child(folium.Marker(
                #     location=[gw_lat, gw_long],
                #     icon=folium.DivIcon(f"""{tower_icon}"""),
                #     popup=f"Gateway: {row['gateway']}\n \
                #         {round(gw_lat,5)},{round(gw_long,5)}"
                #     )
                # )
                uplink_points = []
                uplink_points.append((row['lat'], row['long']))
                uplink_points.append((gw_lat, gw_long))

                # add lines
                tooltip = F"""
                    RSSI:{ row['rssi'] }, SNR:{ row['snr'] }<br>
                    Distance:{row['dist']:.2f}km<br>
                    Device: { dev_eui }<br>
                    Gateway: { row['gateway'] }<br>
                    { row['time'].strftime('%Y-%m-%d %H:%M(%Z)') }
                """
                rssi_gw_group.add_child(
                    folium.PolyLine(
                        uplink_points,
                        tooltip=tooltip,
                        color=row['rssi_color'],
                        weight=4,
                        opacity=1
                    )
                )
        # RSSI for a gateway
        rssi_gw_group.add_to(map_one)

        # now a new snr_gw_group with the SNR markers
        snr_gw_group = folium.FeatureGroup(F"{gateway} - SNR")
        # SNR Markers
        for index, row in frame_stats.iterrows():
            snr_gw_group.add_child(folium.CircleMarker(
                location=(row['lat'], row['long']),
                radius=10,
                popup=f"""
                    GW:{ row['gateway'] }<br>
                    Count:{ row['count'] }<br>
                    RSSI:{row['rssi']},
                    SNR:<strong>{row['snr']}</strong><br>
                    Distance:{row['dist']:.2f}km<br>
                    { row['time'].strftime('%Y-%m-%d %H:%M(%Z)') }
                """,
                color=row['snr_color'],
                fill=False,
                fill_color=row['snr_color'],
                fill_opacity=0.5,
            ))
            # if gw_loc:
            #     snr_gw_group.add_child(folium.Marker(
            #         location=[gw_lat, gw_long],
            #         icon=folium.DivIcon(f"""{tower_icon}"""),
            #         popup=f"Gateway: {row['gateway']}\n \
            #             {round(gw_lat,5)},{round(gw_long,5)}"
            #         ))
        snr_gw_group.add_to(map_one)

        # Add each Tower to Tower_Makers
        tower_markers.add_child(folium.Marker(
            location=[gw_lat, gw_long],
            icon=folium.DivIcon(f"""{tower_icon}"""),
            popup=f"""
                Gateway: {row['gateway']}\n
                {gw_lat},{gw_long}
            """
        ))

    # add Tower Markers to map_one
    tower_markers.add_to(map_one)

    # Now the Best markers. Not per gateway
    best_rssi_makers = folium.FeatureGroup("Best - RSSI")
    # RSSI Markers
    for index, row in frames_df.iterrows():
        best_rssi_makers.add_child(folium.CircleMarker(
            location=(row['lat'], row['long']),
            radius=10,
            popup=f"""
                Count:{ row['count']} ({ row['addr'] })<br>
                RSSI:<strong>{row['rssi']}</strong>,SNR:{row['snr']}<br>
                Distance:{row['dist']:.2f}km<br>
                { row['time'].strftime('%Y-%m-%d %H:%M(%Z)') }
            """,
            color=row['rssi_color'],
            fill=False,
            fill_color=row['rssi_color'],
            fill_opacity=0.5,
        ))
    best_rssi_makers.add_to(map_one)

    best_snr_makers = folium.FeatureGroup("Best - SNR")
    # SNR Markers
    for index, row in frames_df.iterrows():
        best_snr_makers.add_child(folium.CircleMarker(
            location=(row['lat'], row['long']),
            radius=10,
            popup=f"""
                Count:{ row['count']} ({ row['addr'] })<br>
                RSSI:{row['rssi']},SNR:<strong>{row['snr']}</strong><br>
                Distance:{row['dist']:.2f}km<br>
                { row['time'].strftime('%Y-%m-%d %H:%M(%Z)') }
            """,
            color=row['snr_color'],
            fill=False,
            fill_color=row['snr_color'],
            fill_opacity=0.5,
        ))
    best_snr_makers.add_to(map_one)

    folium.LayerControl().add_to(map_one)

    stop_timer = perf_counter()
    map_plot_time = round(stop_timer - start_timer, 1)

    start_timer = perf_counter()
    map_one_html = map_one._repr_html_()
    stop_timer = perf_counter()
    map_html_time = round(stop_timer - start_timer, 1)

    context["map_one"] = map_one_html

    map_time = round(map_plot_time + map_html_time, 1)
    context['map_time'] = map_time

    context['console_messages'] = console_messages
    return render(request, 'geowan/geoView.html', context)
