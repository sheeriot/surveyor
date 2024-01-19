rssi_scale = {
        50: '#e92b96',
        60: '#e72cb3',
        70: '#e42ed0',
        80: '#d92fe2',
        90: '#bb31e0',
        100: '#9e32dd',
        110: '#8234db',
        118: '#6735d8',
        126: '#4e37d6',
        129: '#383bd3',
        132: '#3a55d1',
        134: '#3b6ecf',
        137: '#3d85cc'
}


def rssi_color_lookup(rssi):
    rssi = abs(rssi)

    hex_color = rssi_scale.get(rssi) or rssi_scale[
      min(rssi_scale.keys(), key=lambda key: abs(key-rssi))]

    return hex_color
