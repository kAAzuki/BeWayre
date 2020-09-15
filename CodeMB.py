from flask import Flask, request, render_template
from datetime import datetime
import urllib.request, urllib.parse, urllib.error
import json
import math
import gmplot
import pandas as pd
from math import sin, cos, sqrt, atan2, radians
import webbrowser
import numpy as np
import time

app = Flask(__name__)


@app.route('/')
def home():
    return """
        <html>
        <head>
        <style>
        body, html {
                    height:100%;
                    margin:0;
                }
                .bg{
                    /* The image used */
                    background-image: url("download.jpeg");

                    /* Full height */
                    height: 100%;

                    /* Center and scale the image nicely */
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: cover;
                    }
        </style>
        </head>
        <body>
            <h1>BeWayre</h1>
            <div class = "grandpa">
            <div class = "parent">
            <form action="/safest">

                <label for="lname">What's your location?</label><br>
                    <input type="text" id="location" name="location" placeholder="Location"><br>

                <label for="dest">What's your destination?</label><br>
                    <input type="text" id="destination" name="destination" placeholder="Destination"><br>  

                <label for="route">How many alternative routes do you want? </label><br>
                    <input type="text" id="routes" name="routes" placeholder="Alternative routes"><br> 
                
                <label for="route">which path you want? [fastest, shortest, balanced] </label><br>
                    <input type="text" id="type" name="type" placeholder="path type"><br> 
                <input type='submit' value='Continue'>
            </form>
            </div>
            </div>
            <style>
                
                  input[type=text], select {
                        width: 100%;
                        padding: 12px 20px;
                        margin: 8px 0;
                        display: inline-block;
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        box-sizing: border-box;
                    }

                    /* Style the submit button */
                    input[type=submit] {
                        width: 100%;
                        background-color: #4CAF50;
                        color: white;
                        padding: 14px 20px;
                        margin: 8px 0;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }

                    /* Add a background color to the submit button on mouse-over */
                    input[type=submit]:hover {
                        background-color: #45a049;
                    }

                .grandpa{
                    display: table; height:100%; margin: 0 auto;
                }
                .parent{
                    display:table-cell; vertical-align:middle;
                }
                
            </style>
        </body></html>
        """


# Launch the FlaskPy dev server

def intersect(circle_center, circle_radius, pt1, pt2, full_line=True):
    (p1x, p1y), (p2x, p2y), (cx, cy) = pt1, pt2, circle_center
    (x1, y1), (x2, y2) = (p1x - cx, p1y - cy), (p2x - cx, p2y - cy)
    dx, dy = (x2 - x1), (y2 - y1)
    dr = (dx ** 2 + dy ** 2) ** .5
    big_d = x1 * y2 - x2 * y1
    discriminant = circle_radius ** 2 * dr ** 2 - big_d ** 2

    if x1 ** 2 + y1 ** 2 - circle_radius ** 2 <= 0 and x2 ** 2 + y2 ** 2 - circle_radius ** 2 <= 0:
        return 1

    if discriminant < 0:
        return 0

    else:
        intersections = [
            (cx + (big_d * dy + sign * (-1 if dy < 0 else 1) * dx * discriminant ** .5) / dr ** 2,
             cy + (-big_d * dx + sign * abs(dy) * discriminant ** .5) / dr ** 2)

            for sign in ((1, -1) if dy < 0 else (-1, 1))]  # This makes sure the order along the segment is correct

        if not full_line:  # If only considering the segment, filter out intersections that do not fall within the segment
            fraction_along_segment = [(xi - p1x) / dx if abs(dx) > abs(dy) else (yi - p1y) / dy for xi, yi in
                                      intersections]
            intersections = [pt for pt, frac in zip(intersections, fraction_along_segment) if 0 <= frac <= 1]
        x, y = intersections[0][0], intersections[0][1]
        xx, yy = intersections[1][0], intersections[1][1]
        first = p1x <= x <= p2x and p1y <= y <= p2y
        sec = p1x <= xx <= p2x and p1y <= yy <= p2y

        if first or sec:
            return 1

        else:
            return 0


def geo(address):
    api_key = False
    if api_key is False:
        api_key = 42
        serviceurl = 'http://py4e-data.dr-chuck.net/json?'
    else:
        serviceurl = 'https://maps.googleapis.com/maps/api/directions/outputFormat?parameters'
    parms = dict()
    parms['address'] = address
    if api_key is not False: parms['key'] = api_key
    url = serviceurl + urllib.parse.urlencode(parms)
    uh = urllib.request.urlopen(url)
    data = uh.read().decode()
    try:
        js = json.loads(data)
    except:
        js = None
    if not js or 'status' not in js or js['status'] != 'OK':
        print('==== Failure To Retrieve ====')
    id1 = js["results"][0]["geometry"]['location']['lat']
    id2 = js["results"][0]["geometry"]['location']['lng']
    return id1, id2


def dist(waypoint00, waypoint01, waypoint10, waypoint11):
    def rad(deg):
        radn = (deg * (math.pi)) / 180
        return radn

    lat1 = rad(waypoint00)
    lat2 = rad(waypoint10)
    lng1 = rad(waypoint01)
    lng2 = rad(waypoint11)

    del_phi = lat2 - lat1
    del_lam = lng2 - lng1

    l = sin(del_phi / 2)
    m = sin(del_lam / 2)
    a = pow(l, 2) + cos(lat1) * cos(lat2) * (pow(m, 2))
    c = 2 * math.asin(math.sqrt(a))
    R = 6373
    d = R * c
    return d


def weather(lat1, lng1):
    wurl = 'http://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&APPID=fd88f5a3b637e917d5ed48d9d6b53335'.format(
        lat1, lng1)
    uh1 = urllib.request.urlopen(wurl)
    data1 = uh1.read().decode()
    try:
        js1 = json.loads(data1)
    except:
        js1 = None
    visibility = 10000
    js2 = (js1['weather'][0]['main'])
    if len(js2) > 12:
        visibility = js1['visibility']
        if (visibility < 1000):
            return 7
    clouds = js1['clouds']['all']
    wind_speed = js1['wind']['speed']
    if (js2 == 'extreme'):
        return 9

    elif js2 == 'clear' or (js2 == 'Clouds' and clouds < 85):
        if wind_speed > 45:
            return 4
        else:
            return 1
    elif js2 == 'Rain' or clouds > 85 or js2 == 'Drizzle':
        if wind_speed > 45:
            return 5
        else:
            return 2
    elif js2 == 'Snow':
        if wind_speed > 45:
            return 6
        else:
            return 3
    else:
        return 10

def traffic(lat1,lng1,lat2,lng2):
    turl = "https://traffic.ls.hereapi.com/traffic/6.0/incidents.json?corridor={}%2C{}%3B{}%2C{}%3B1500&apiKey=U2odxl9gB5Zv6EZTMw30nvGQzG9B39C1D6h-Xzarg4M".format(
        lat1, lng1, lat2, lng2)
    uh1 = urllib.request.urlopen(turl)
    data2 = uh1.read().decode()
    try:
        js3 = json.loads(data2)
    except:
        js3 = None

    n = len(js3["TRAFFICITEMS"]["TRAFFICITEM"])
    critc = []
    lat = []
    lng = []
    for i in range(n):
        critc.append(abs(int(js3["TRAFFICITEMS"]["TRAFFICITEM"][i]["CRITICALITY"]["ID"])-3))
        lat.append(js3["TRAFFICITEMS"]["TRAFFICITEM"][i]["LOCATION"]["GEOLOC"]["ORIGIN"]["LATITUDE"])
        lng.append(js3["TRAFFICITEMS"]["TRAFFICITEM"][i]["LOCATION"]["GEOLOC"]["ORIGIN"]["LONGITUDE"])
        return critc,lat,lng


@app.route('/safest')
def safest():
    t = time.time()
    # username = request.args.get('username', 'World')
    # favfood = request.args['favfood']
    waypt01 = request.args.get('location')
    # waypt01=input("Enter the Starting location: ")
    lat1, lng1 = geo(waypt01)

    waypt02 = request.args.get('destination')
    # waypt02=input("Enter the destination: ")
    lat2, lng2 = geo(waypt02)
    critic,tlat,tlng=traffic(lat1,lng1,lat2,lng2)
    # print(lat1,lng1,lat2,lng2)
    mode1 = request.args.get('type')
    #mode1 = 'balanced'
    #mode1 = request.args.get('')
    #mode1=input("Enter the Route Mode[fastest,shortest,balanced]: ")
    #mode2=input("Enter the Vehicle Type:[car|pedestrian|carHOV|publicTransport|publicTransportTimeTable|truck|bicycle]: ")
    surl = 'https://route.ls.hereapi.com/routing/7.2/calculateroute.json?waypoint0={}%2C{}&waypoint1={}%2C{}&mode={}%3B{}&'.format(
        lat1, lng1, lat2, lng2, mode1, 'car')

    alternatives = request.args.get('routes')
    # alternatives=input('Enter the no. of alternative routes:')
    api_Key = 'U2odxl9gB5Zv6EZTMw30nvGQzG9B39C1D6h-Xzarg4M'
    url = surl + urllib.parse.urlencode({'alternatives': alternatives, 'apiKey': api_Key})
    uh = urllib.request.urlopen(url)
    data = uh.read().decode()
    try:
        js = json.loads(data)
    except:
        js = None
    lat = []
    lng = []

    for j in range(len(js['response']['route'])):
        lt = []
        ln = []

        for i in range(len(js['response']['route'][j]['leg'][0]['maneuver'])):
            lt.append(js['response']['route'][j]['leg'][0]['maneuver'][i]['position']['latitude'])
            ln.append(js['response']['route'][j]['leg'][0]['maneuver'][i]['position']['longitude'])
        lat.append(lt)
        lng.append(ln)
    p = []
    data = pd.read_csv("./Data/data_temp.csv")
    # l = [i for i in range(425)]+[-1]
    lt0 = [data[data.cluster == i].mean()[0] for i in range(425)]
    lg0 = [data[data.cluster == i].mean()[1] for i in range(425)]
    # for i in l:
    # lt0.append(data[data.cluster == i].mean()[0])
    # lg0.append(data[data.cluster == i].mean()[1])
    r1 = .03

    data1 = pd.read_csv("./Data/data_temp (1).csv")
    # l1 = [i for i in range(230)]+[-1]
    lt1 = [data1[data1.cluster == i].mean()[0] for i in range(230)]
    lg1 = [data1[data1.cluster == i].mean()[1] for i in range(230)]
    # for i in l1:
    # lt1.append(data1[data1.cluster == i].mean()[0])
    # lg1.append(data1[data1.cluster == i].mean()[1])
    cf=[]
    r=[]
    p = []
    m = []
    weath = []
    r1=.03
    junct_count = []
    for j in range(len(lat)):
        start_pt = [lat[j][1], lng[j][1]]
        q = []
        n = []
        e=[]
        c=[]
        junct_count.append(len(lat[j]) - 1)
        w = [(weather(start_pt[0], start_pt[1]))]
        for i in range(len(lat[j]) - 1):
            if dist(start_pt[0], start_pt[1], lat[j][i + 1], lng[j][i + 1]) > 8:
                start_pt = [lat[j][i + 1], lng[j][i + 1]]
                w.append(weather(start_pt[0], start_pt[1]))
            pt1 = [lat[j][i], lng[j][i]]
            pt2 = [lat[j][i + 1], lng[j][i + 1]]
            for k in range(len(lt0)):
                circle_centre = [lt0[k], lg0[k]]
                a = intersect(circle_centre, r1, pt1, pt2)
                n.append(a)
            for k in range(len(lt1)):
                circle_centre1 = [lt1[k], lg1[k]]
                a1 = intersect(circle_centre1, r1, pt1, pt2)
                q.append(a1)
            for k in range(len(tlat)):
                circle_centre2=[tlat[k],tlng[k]]
                a2=intersect(circle_centre2,r1,pt1,pt2)
                if a2>0:
                    c.append(critic[k])
                e.append(a2)        

            
        m.append(n)
        p.append(q)
        weath.append(w)
        cf.append(c)
        r.append(e)

    dang_index1 = []
    for i in range(len(m)):
        total = 0
        for j in range(len(m[i])):
            total = total + m[i][j]
        dang_index1.append(total)

    dang_index2 = []
    for i in range(len(p)):
        total = 0
        for j in range(len(p[i])):
            total = total + p[i][j]
        dang_index2.append(total)

    dang_index3 = []
    for i in range(len(weath)):
        total = 0
        for j in range(len(weath[i])):
            total = total + weath[i][j]
        dang_index3.append(total / (len(weath[i])))

    dang_index4 = junct_count
    dang_index5=[]
    for i in range(len(cf)):
        total=0
        for j in range(len(cf[i])):
            total = total + cf[i][j]        
    dang_index5.append(total)

    # for i in range(len(m)):
    #     print('Route No.',i+1)
    #     print("Length of route",i+1,':',js['response']['route'][i]['summary']['distance'])
    #     print("Total traffic time of route",i+1,':',js['response']['route'][i]['summary']['trafficTime'])
    #     print("Road accident Points on route",i+1,': ',dang_index1[i])
    #     print("Vehicle Crime Points on route", i+1, ': ', dang_index2[i])
    #     print("Bad Weather probability on route",i+1, ': ', dang_index3[i])
    #     print("No. of junctions on route", i+1, ': ', dang_index4[i])
    sp_lmt = []
    for i in range(len(m)):
        dis = (js['response']['route'][i]['summary']['distance']) / js['response']['route'][i]['summary']['trafficTime']
        sp_lmt.append(dis)
    aka = 0.5 * np.array(dang_index1) + 0.5 * np.array(dang_index2) + 0.04 * np.array(
            dang_index3) + 0.376 * np.array(dang_index4) + 0.096 * np.array(sp_lmt)+.25*np.array(dang_index5)
    i = np.argmin(aka)
    lati = (min(min(lat)) + max(max(lat))) / 2
    lngi = (min(min(lng)) + max(max(lng))) / 2
    gmap3 = gmplot.GoogleMapPlotter(lati, lngi, 8)

    # for i in range(len(lat)):
    gmap3.scatter(lat[i], lng[i], '#FF0000', size=15, marker=True)
    gmap3.plot(lat[i], lng[i], 'cornflowerblue', edge_width=5)
    gmap3.draw("./map1.html")
    new = 1
    url = "./map1.html"

    webbrowser.open(url,new=new)
    print(time.time() - t)
    #return render_template('./map1.html')
    return 'map'


app.run(host="localhost", debug=True)
