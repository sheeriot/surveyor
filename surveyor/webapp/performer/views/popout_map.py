from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from time import perf_counter
import dateutil.parser
import dateutil.tz
import pandas as pd
from geopy.distance import geodesic

import redis
import json
import folium

# from icecream import ic

from celery.result import AsyncResult
from device.models import InfluxSource, BucketDevice
from device.locate import pluscode2latlon

from surveyor.settings import TIME_ZONE
from ..colorscales import color_lookup_red0
from surveyor.tower import tower_svg


@login_required
def popoutMap(request, task_id=None):
    """
    This function takes in the device summary dataframe and the device gateway dataframe and returns a folium map.
    """

    # task_id = request.GET.get('task_id', None)
    if timezone.get_current_timezone():
        tz = str(timezone.get_current_timezone())
    else:
        tz = TIME_ZONE
    zulu_tz = dateutil.tz.gettz('UTC')
    local_tz = dateutil.tz.gettz(tz)
    if task_id is None:
        return HttpResponse('No Task_ID was given.')
    task = AsyncResult(task_id)
    kwargs = eval(task.kwargs)
    center_latitude, center_longitude = kwargs['center']
    if center_latitude and center_latitude:
        rings = kwargs['rings']
        map_center = True
    else:
        map_center = False

    source_id, meas, start_mark, end_mark = eval(task.args)

    zulu_tz = dateutil.tz.gettz('UTC')
    source = InfluxSource.objects.get(pk=source_id)
    source_name = source.name
    if task.state == 'SUCCESS':
        report_status, totals_dict = task.result
        if report_status.lower().startswith(("failed", "empty")):
            return HttpResponse(F'Report Status: {report_status}')

        redis_client = redis.Redis(host='redis', port=6379, db=0)

        # reconstitute the dataframes from redis
        gw_info_json = redis_client.get(f'{task_id}:gw_info_df')
        gw_info_dict = json.loads(gw_info_json)
        gw_info_df = pd.DataFrame(gw_info_dict)

        device_uplinks_json = redis_client.get(f'{task_id}:device_uplinks_df')
        device_uplinks_dict = json.loads(device_uplinks_json)
        device_uplinks_df = pd.DataFrame(device_uplinks_dict)

        # fix the timestamps
        device_uplinks_df['frame_first'] = pd.to_datetime(device_uplinks_df['frame_first'],
                                                          unit='ms').dt.tz_localize(zulu_tz)
        device_uplinks_df['frame_first'] = device_uplinks_df['frame_first'].dt.tz_convert(local_tz)
        device_uplinks_df['frame_last'] = pd.to_datetime(device_uplinks_df['frame_last'],
                                                         unit='ms').dt.tz_localize(zulu_tz)
        device_uplinks_df['frame_last'] = device_uplinks_df['frame_last'].dt.tz_convert(local_tz)

        device_gw_json = redis_client.get(f'{task_id}:device_gw_df')
        device_gw_dict = json.loads(device_gw_json)
        device_gw_df = pd.DataFrame(device_gw_dict)

        # reconstitute the device_locs_df
        device_loc_json = redis_client.get(f'{task_id}:device_loc_df')
        device_loc_dict = json.loads(device_loc_json)
        device_loc_df = pd.DataFrame(device_loc_dict)

        devices_seen = list(device_uplinks_df['dev_eui'])
        if device_loc_df.empty:
            devices_withloc = []
        else:
            devices_withloc = list(device_loc_df['dev_eui'])
            devices_missing = set(devices_withloc) - set(devices_seen)
            devices_missing_df = device_loc_df[device_loc_df['dev_eui'].isin(devices_missing)]

    else:
        # pass task.state as report_status if NOT SUCCESS
        report_status = task.state
        device_uplinks_df = None
        device_gw_df = None
        gw_info_df = None
        return HttpResponse(F'<hr>Task State: {report_status} - no Maps')

    context = {
        'report_status': report_status,
        'source_id': source_id,
        'source_name': source_name,
        'meas': meas,
        'start_mark': start_mark,
        'end_mark': end_mark,
    }

    # only able to map devices with locations
    if 'pluscode' in device_uplinks_df.columns:
        device_loc_df = device_uplinks_df[['dev_eui', 'pluscode']].copy().dropna()
        device_loc_df['lat'], device_loc_df['long'] = zip(*device_loc_df['pluscode'].apply(pluscode2latlon))
        device_loc_df = device_loc_df.drop(columns=['pluscode']).set_index('dev_eui')
    else:
        device_loc_df = pd.DataFrame(list(BucketDevice.objects.filter(influx_source=source).values()))
        if device_loc_df.shape[0] > 0:
            device_loc_df = device_loc_df.drop(columns=['id', 'influx_source_id'])
            device_loc_df['dev_eui'] = device_loc_df['dev_eui'].str.lower()
            device_loc_df = device_loc_df.set_index('dev_eui')
        else:
            return HttpResponse('<hr><h4>No Map</h4>No Device Location Info, no Map!')

    device_uplinks_df = device_uplinks_df.set_index('dev_eui')

    gw_info_df = gw_info_df.set_index('gateway')

    # create an indexed Pandas series on gateway
    devices_per_gateway = device_gw_df.groupby('gateway')['dev_eui'].nunique().astype(int)
    gw_info_df['devices'] = gw_info_df.index.map(devices_per_gateway)

    # context['gw_info_df'] = gw_info_df.reset_index().sort_values('devices', ascending=False)

    # add some color
    device_uplinks_df['uplinks_pdr_color'] = device_uplinks_df['uplinks_pdr'].apply(lambda x:
                                                                                    color_lookup_red0(x * 100))
    # rssi_mean
    rssiscale_lower = -115
    rssiscale_upper = -85
    rssiscale_range = rssiscale_upper - rssiscale_lower
    device_gw_df['rssi_color'] = (device_gw_df['rssi_mean']
                                  .apply(lambda x:
                                  color_lookup_red0((x - rssiscale_lower) / rssiscale_range * 100))
                                  )
    # snr_mean
    snrscale_lower = -10
    snrscale_upper = 10
    snrscale_range = snrscale_upper - snrscale_lower
    device_gw_df['snr_color'] = (device_gw_df['snr_mean']
                                 .apply(lambda x:
                                 color_lookup_red0((x - snrscale_lower) / snrscale_range * 100))
                                 )

    tower_icon = tower_svg()

    if not map_center:
        device_loc_df = device_loc_df.dropna()
        center_latitude = round(device_loc_df['lat'].mean(), 5)
        center_longitude = round(device_loc_df['long'].mean(), 5)

    start_timer = perf_counter()

    # Create the main map
    popout_map = folium.Map(
        location=(center_latitude, center_longitude),
        zoom_start=14,
        scrollWheelZoom=False,
        control_scale=True,
        tiles="cartodbpositron",
    )

    # create rings
    if map_center:
        ring_layer = folium.FeatureGroup("Radius")
        # Make Rings
        max_ring = 11
        for radius in range(rings, max_ring, rings):
            folium.Circle(
                location=[center_latitude, center_longitude],
                radius=radius * 1000,
                color='violet',
                opacity=0.75,
                weight=3,
                tooltip=f"{radius}km radius",
            ).add_to(ring_layer)
        # Mark the Center
        folium.CircleMarker(
            location=[center_latitude, center_longitude],
            radius=5,
            fill=True,
            fill_opacity=1,
            color='violet',
            opacity=1,
            weight=5,
            popup=f"Center:\n{center_latitude}\n{center_longitude}"
        ).add_to(ring_layer)
        ring_layer.add_to(popout_map)

    # # Connect to Redis to save gateway/device stats
    # redis_client = redis.Redis(host='redis', port=6379, db=0)

    top_gateways = (device_gw_df.groupby('gateway').size().nlargest(10).index.tolist())

    towers_layer = folium.FeatureGroup(name="Gateways", control=False)
    # lines should be an form option
    lines = True
    if lines:
        lines_layer = folium.FeatureGroup(name="Uplink Lines", show=False)

    for gateway, device_gw_stats in device_gw_df.groupby('gateway'):

        # does this gateway have a location
        gw_loc = True
        try:
            gateway_lat, gateway_long = gw_info_df.loc[gateway, ['lat', 'long']]
        except KeyError:
            gateway_lat, gateway_long = None, None
            gw_loc = False

        # map all possible towers
        if gw_loc:
            towers_layer.add_child(folium.Marker(
                location=[gateway_lat, gateway_long],
                icon=folium.DivIcon(f"""{ tower_icon }<br>{ gateway }"""),
                tooltip=f"""
                Gateway: {gateway}<br>
                {gateway_lat}, {gateway_long}"
                """
                ))

        # show all lines possible on one layer
        if lines:
            gw_lines_df = device_gw_stats[[
                'dev_eui',
                'lat',
                'long',
                'gw_lat',
                'gw_long',
                'rssi_mean',
                'snr_mean',
                'rssi_color'
            ]].copy().dropna()
            # map lines with valid device and gateway locations
            for index, row in gw_lines_df.iterrows():
                uplink_points = [
                    [row['lat'], row['long']],
                    [row['gw_lat'], row['gw_long']],
                ]
                dist_km = round(
                    geodesic(
                        (row['lat'], row['long']),
                        (row['gw_lat'], row['gw_long'])
                    ).km,
                    3
                )

                # add lines
                tooltip = F"""
                    Device: { row['dev_eui'] }<br>
                    Gateway: { gateway }<br>
                    RSSI:{ row['rssi_mean'] }, SNR:{ row['snr_mean'] }<br>
                    Distance:{ dist_km } km
                """
                lines_layer.add_child(
                    folium.PolyLine(
                        locations=uplink_points,
                        tooltip=tooltip,
                        color=row['rssi_color'],
                        weight=4,
                        opacity=1
                    )
                )

        # gateways and lines mapped, prune stats for per gateway layers
        device_gw_stats = device_gw_stats.dropna(subset=['lat', 'long'])

        if gateway in top_gateways:
            # create rssi and snr layers for each top 5 gateway
            gw_rssi_layer = folium.FeatureGroup(name=F"{gateway} - RSSI mean", show=False)
            # gw_snr_layer = folium.FeatureGroup(name=F"{gateway} - SNR mean", show=False)

            #
            device_gw_stats = device_gw_stats.reset_index().dropna(subset=['lat', 'long'])
            for index, row in device_gw_stats.iterrows():
                popup = F"""
                    G:{ gateway }<br>
                    D:{ row['dev_eui'] }<br>
                    -----------------------<br>
                    RSSI: { row['rssi_mean'] } (s:{ row['rssi_std'] })<br>
                    SNR Mean: { row['snr_mean'] } (s:{ row['snr_std'] })<br>
                    Received: { row['frame_count'] } of { row['uplinks_total'] }
                """
                gw_rssi_layer.add_child(folium.Marker(
                    location=(row['lat'], row['long']),
                    popup=popup,
                    icon=folium.Icon(
                        icon='circle',
                        prefix='fa',
                        icon_color=row['rssi_color']
                    )
                ))
                # gw_snr_layer.add_child(folium.Marker(
                #     location=(row['lat'], row['long']),
                #     popup=f" \
                #         D:{row['dev_eui']}<br> \
                #         -----------------------<br> \
                #         RSSI Mean: {row['rssi_mean']:.0f} <br>\
                #         SNR Mean: {row['snr_mean']:.1f}<br> \
                #         Received: {row['frame_count']} of {row['uplinks_total']}",
                #     icon=folium.Icon(
                #         icon='circle',
                #         prefix='fa',
                #         icon_color=row['snr_color']
                #     )
                # ))
            # if there is a gateway location, add it to both gateway maps SNR and RSSI
            # if gw_loc:
            #     gw_rssi_layer.add_child(folium.Marker(
            #         location=[gateway_lat, gateway_long],
            #         icon=folium.DivIcon(f"""{tower_icon}"""),
            #         popup=f"Gateway: { gateway }\n \
            #             {round(gateway_lat,5)},{round(gateway_long,5)}"
            #         )
            #     )
                # gw_snr_layer.add_child(folium.Marker(
                #     location=[gateway_lat, gateway_long],
                #     icon=folium.DivIcon(f"""{tower_icon}"""),
                #     popup=f"Gateway: { gateway }\n \
                #         {round(gateway_lat,5)},{round(gateway_long,5)}"
                #     )
                # )
            # gw_snr_layer.add_to(popout_map)
            gw_rssi_layer.add_to(popout_map)

    # add towers layer
    lines_layer.add_to(popout_map)
    towers_layer.add_to(popout_map)

    # Packet Delivery Rate aka Uplinks Success Rate
    # only map devices with locations
    device_successmap_df = device_uplinks_df.dropna(subset=['lat', 'long'])
    # map devices with uplinks_total > 1
    successrate_layer = folium.FeatureGroup("Packet Delivery Ratio")
    for index, row in device_successmap_df[device_successmap_df['uplinks_total'] > 1].iterrows():
        successrate_layer.add_child(folium.CircleMarker(
            location=(row['lat'], row['long']),
            radius=5,
            color=row['uplinks_pdr_color'],
            fill=True,
            fill_color=row['uplinks_pdr_color'],
            fill_opacity=0.7,
            popup=f"""
                D:{index}<br>
                -----------------------<br>
                Uplinks Received: {row['uplinks_received']}<br>
                Uplinks Missed: {row['uplinks_missed']}<br>
                Uplinks Total: {row['uplinks_total']}<br>
                Uplinks PDR: {row['uplinks_pdr']*100:.1f}%<br>
                Gateways: {row['gateways']}
                """,
        ))
    successrate_layer.add_to(popout_map)

    singles_layer = folium.FeatureGroup("Single Uplinks")
    for index, row in device_successmap_df[device_successmap_df['uplinks_total'] == 1].iterrows():
        singles_layer.add_child(folium.CircleMarker(
            location=(row['lat'], row['long']),
            radius=5,
            color='indianred',
            fill=True,
            fill_color='indianred',
            fill_opacity=0.7,
            popup=f"""
                D:{index}<br>
                ----Single Uplinks --<br>
                Frames Received: { row['frames_received'] }<br>
                Gateways: { row['gateways'] }<br>
                First:<br><small>{ row['frame_first']:%Y-%m-%d %H:%M(%Z) }</small><br>
                Last:<br><small>{ row['frame_last']:%Y-%m-%d %H:%M(%Z) }</small>
                """,
        ))
    singles_layer.add_to(popout_map)

    if not devices_missing_df.empty:
        missingdevices_layer = folium.FeatureGroup("Missing Devices")
        for index, row in devices_missing_df.iterrows():
            missingdevices_layer.add_child(folium.CircleMarker(
                location=(row['lat'], row['long']),
                radius=5,
                color='black',
                fill=True,
                fill_color='black',
                fill_opacity=0.7,
                popup=f"""
                    D:{row['dev_eui']}<br>
                    --missing--<br>
                    Marker: {row['marker']}<br>
                    Address: {row['address']}<br>
                    """,
            ))
        missingdevices_layer.add_to(popout_map)

    folium.LayerControl().add_to(popout_map)

    stop_timer = perf_counter()
    map_plot_time = round(stop_timer - start_timer, 1)
    start_timer = perf_counter()

    popout_map_html = popout_map._repr_html_()

    context["popout_map_html"] = popout_map_html

    stop_timer = perf_counter()
    map_html_time = round(stop_timer - start_timer, 1)
    map_time = round(map_plot_time + map_html_time, 1)
    context['map_time'] = map_time
    context['request'] = request

    rendered = render_to_string('performer/popout_map.html', context)

    return HttpResponse(rendered)
