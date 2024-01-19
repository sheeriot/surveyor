# 0 = Green
scale_greenyellowred = {
    0: '#57bb8a',
    5: '#63b682',
    10: '#73b87e',
    15: '#84bb7b',
    20: '#94bd77',
    25: '#a4c073',
    30: '#b0be6e',
    35: '#c4c56d',
    40: '#d4c86a',
    45: '#e2c965',
    50: '#f5ce62',
    55: '#f3c563',
    60: '#e9b861',
    65: '#e6ad61',
    70: '#ecac67',
    75: '#e9a268',
    80: '#e79a69',
    85: '#e5926b',
    90: '#e2886c',
    95: '#e0816d',
    100: '#dd776e',
}
# 0 = Red
scale_redyellowgreen = {
    100: '#57bb8a',
    95: '#63b682',
    90: '#73b87e',
    85: '#84bb7b',
    80: '#94bd77',
    75: '#a4c073',
    70: '#b0be6e',
    65: '#c4c56d',
    60: '#d4c86a',
    55: '#e2c965',
    50: '#f5ce62',
    45: '#f3c563',
    40: '#e9b861',
    35: '#e6ad61',
    30: '#ecac67',
    25: '#e9a268',
    20: '#e79a69',
    15: '#e5926b',
    10: '#e2886c',
    5: '#e0816d',
    0: '#dd776e',
}

scale_old = {
        90: '#2cba00',
        95: '#a3ff00',
        100: '#fff400',
        105: '#ffa700',
        110: '#ff0000',
        115: '#ff00c8',
        120: '#ff00c8',
}

# def rssi_color_lookup(rssi):
#     rssi = abs(rssi)
#     hex_color = scale_old.get(rssi) or scale_old[
#       min(scale_old.keys(), key = lambda key: abs(key-rssi))
#     ]
#     return hex_color


def color_lookup_green0(percent):
    hex_color = scale_greenyellowred.get(percent) or scale_greenyellowred[
      min(scale_greenyellowred.keys(), key=lambda key: abs(key-percent))
    ]
    return hex_color


def color_lookup_red0(percent):
    hex_color = scale_redyellowgreen.get(percent) or scale_redyellowgreen[
      min(scale_redyellowgreen.keys(), key=lambda key: abs(key-percent))
    ]
    return hex_color
