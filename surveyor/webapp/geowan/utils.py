import folium


def makeMap(loc=[30.4235, -97.9326], zoom=14):  # creates map, need to put output in context
    m = folium.Map(location=loc, zoom_start=zoom)
    m = m._repr_html_()
    return m
