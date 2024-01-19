import folium
# from folium.plugins import HeatMap
import numpy as np
import pandas as pd
# import geopandas
# import networkx as nx
# from libpysal.cg import voronoi_frames
# from libpysal import weights

# Lots of cruft to remove from this file...


def geoDistance(lat1, long1, lat2, long2):

    # if any values are not available, send back 0
    if pd.isna(lat1) or pd.isna(long1) or pd.isna(lat2) or pd.isna(long2):
        return 0
    # print(F'lat1:{lat1},long1:{long1},lat2:{lat2},long2:{long2}')
    # print(F'lat1t:{type(lat1)},long1t:{type(long1)},lat2t:{type(lat2)},long2t:{type(long2)}')
    # convert to radians and use Haversine formula
    dlon = np.radians(long2 - long1)
    dlat = np.radians(lat2 - lat1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))

    # radius of the earth in km
    r = 6371
    return round(c * r, 2)


def makeMap(loc=[30.4235, -97.9326], zoom=14):  # creates map, need to put output in context
    m = folium.Map(location=loc, zoom_start=zoom)
    m = m._repr_html_()
    return m

# create heat map of data, should have shape [[lat,long,weight],[lat2,long2,weight2],...]
# def makeHeatMap(data,zoom=12):

#     #find starting location, center of the extreams of the locaton
#     initLat = (np.min(data[:,0])+np.max(data[:,0]))/2
#     initLong = (np.min(data[:,1])+np.max(data[:,1]))/2

#     #initalize map
#     hmap = folium.Map(location=[initLat,initLong], tiles="OpenStreetMap", zoom_start=zoom)

#     #create heat map layer and add it
#     HeatMap(data,radius=5).add_to(hmap)

#     #convert map to html, needed to pass to template
#     return(hmap._repr_html_())

# #normalizes the rssi data, maps values between zero and one
# #can be set to normalize between given values
# def normRssi(rssiArr,Amin=None,Amax=None):

#     #set minimum and maximums if not defined
#     if not Amin:
#         Amin = np.min(rssiArr)
#     if not Amax:
#         Amax = np.max(rssiArr)

#     #extra .00001 added to account for heat maps inturpret heat of 0
#     return (rssiArr - Amin)/(Amax - Amin) + .00001

# #generates list of points and heats using the data given
# #data given as a pandas dataframe with columns 'Latitude', 'Longitude', and 'weights'
# #also takes in the resolution that the image, [points/km]
#     #returns a list of points with their heat values
#     def pointHeats(df,resolution):

#         #find bounds of heat map
#         leftBound = np.amin(df['Longitude'])
#         rightBound = np.amax(df['Longitude'])
#         topBound = np.amax(df['Latitude'])
#         bottomBound = np.amin(df['Latitude'])

#         #the number of points in each direction
#         numPointsVert = int((topBound-bottomBound)*111.3195*resolution)
#         numPointsHorz = int((rightBound-leftBound)*111.3195*resolution*np.cos(topBound*np.pi/180))

#         #convert pandas dataframe to geopandas
#         gdf = geopandas.GeoDataFrame(
#             df, geometry=geopandas.points_from_xy(df.Longitude, df.Latitude))

#         #create coordinates array from geopandas dataframe
#         coordinates = np.column_stack((gdf.geometry.x,gdf.geometry.y,df['weights']))

#         #generate voronoi cells
#         cells, _ = voronoi_frames(coordinates[:,:2], clip="convex hull")

#         #generate delaunay connections from the voronoi cells
#         delaunay = weights.Rook.from_dataframe(cells)

#         #generate the networkx graph
#         delaunay_graph = delaunay.to_networkx()

#         #merge the nodes back to there positions for plotting, returns a dictionary of the
#         #node index as the key and the coordinates as the value
#         positions = dict(zip(delaunay_graph.nodes, coordinates))

#         #find triangles, returns a list of all trinalges in the form of arrays of there indexes
#         #therefor you can access the different positions with positions[tLoops[tnum][tvert]]
#         #where tnum is the triangle number and tvert is the vertici number
#         tLoops = [x for x in nx.enumerate_all_cliques(delaunay_graph) if len(x)==3]

#         #go through triangles and generate side vector info and dot product info, will be used later
#         triangels = {}
#         for i,tLoop in enumerate(tLoops):

#             #the three points
#             A = positions[tLoop[0]]
#             B = positions[tLoop[1]]
#             C = positions[tLoop[2]]

#             #side vectors
#             v0 = B[:2]-A[:2]
#             v1 = C[:2]-A[:2]

#             #dot products
#             dot00 = np.dot(v0,v0)
#             dot01 = np.dot(v0,v1)
#             dot11 = np.dot(v1,v1)

#             #define the normal vector to the triangle
#             norm = np.cross(B-A,C-A)

#             # add information to triangles,
#             # weightF is the weights function, the plain that passes through the 3 points
#             triangels[i] = {'A':A,
#                             'v0':v0,
#                             'v1':v1,
#                             'dot00':dot00,
#                             'dot01':dot01,
#                             'dot11':dot11,
#                             'invDenom':1/(dot00*dot11-dot01*dot01),
#                             'norm':norm}

#         #create a function that will determine a points values based on where it is
#         #this will allow us to vectorize it to make the code quicker
#         #takes in a points p [longditude,latitude], and the last triangle a point was found in,
#         #allong with the list of triangles
#         #returns the points weight
#         #assume the positions of data = positions
#         def teriform(lastT,p):

#             #check if the point is in the last triangle
#             if(inside(lastT,p)):

#                 #calculate weight
#                 weight = (lastT['norm'][0]*(p[0]-lastT['A'][0])
#                           +lastT['norm'][1]*(p[1]-lastT['A'][1]))/(-lastT['norm'][2])+lastT['A'][2]
#                 return(lastT,weight)

#             #find the triangle that the point belongs to
#             for t in triangels:

#                 #given the key need the value
#                 t = triangels[t]

#                 #check if the point falls in the triangle
#                 if(inside(t,p)):

#                     #calculate weight
#                     weight = (t['norm'][0]*(p[0]-t['A'][0])+t['norm'][1]*(p[1]-t['A'][1]))/(-t['norm'][2])+t['A'][2]

#                     #return the calculated weight
#                     return(t,weight)

#             #if the point is found to not be in a trangle than return 0
#             return(lastT,0)

#         #tests if the point is inside the triangle, takes in the triangle dictionary and the point
#         #test defined here: https://blackpawn.com/texts/pointinpoly/
#         def inside(t,p):

#             #find components specific to this point
#             v2 = p-t['A'][:2]
#             dot02 = np.dot(t['v0'],v2)
#             dot12 = np.dot(t['v1'],v2)

#             #Compute barycentric coordinates
#             u = (t['dot11'] * dot02 - t['dot01'] * dot12) * t['invDenom']
#             v = (t['dot00'] * dot12 - t['dot01'] * dot02) * t['invDenom']

#             #check if point is inside triangle
#             if(u>=0 and v>=0 and u+v<1):
#                 return(True)
#             return(False)

#         #generate a grid of points with a determined resolution and with the givin size
#         latPoints = np.linspace(bottomBound,topBound,numPointsVert)
#         longPoints = np.linspace(leftBound,rightBound,numPointsHorz)
#         Lat, Long = np.meshgrid(latPoints,longPoints)

#         #create empty list to hold the points, [[lat,long,weight], [lat,long,weight], ...]
#         points = np.zeros(shape=(numPointsHorz*numPointsVert,3))

#         #add points to the data
#         points[:,0] = Lat.reshape((numPointsHorz*numPointsVert,))
#         points[:,1] = Long.reshape((numPointsHorz*numPointsVert,))

#         #inisialize the last triangle veriable, it can be a random triangle to start with
#         lastT = triangels[0]

#         #Generate weights
#         for point in points:
#             #possible speed up, sort the tLoops list in a way that you can limit the number of
#             #triangles that need to be checked to see if they enclude the point
#             lastT, point[2] = teriform(lastT,[point[1],point[0]])

#         #only keep data with a non zero weights
#         points = points[points[:,2]!=0]

#         #return point list
#         return(points)
