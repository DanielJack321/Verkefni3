import ctypes
import re
import platform
import matplotlib.pyplot as plt
import os
import sys
import numpy as np

# Get the current working directory
current_directory = os.getcwd()

# Add the current working directory to sys.path
if current_directory not in sys.path:
    sys.path.append(current_directory)
(tSHIP,tSTAT,tWAYP,tENDP,tPORT) = (1,2,3,4,5)

# Detect the platform
if platform.system() == "Windows":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("the directory is:", script_dir)
    os.add_dll_directory(script_dir)
    # Load the DLL
    lib = ctypes.WinDLL("lib/utils.dll")
elif platform.system() == "Darwin":  # For macOS
    # Load the .dylib file on macOS
    lib = ctypes.CDLL('lib/utils.dylib')
else:
    # Load the .so file on Linux
    lib = ctypes.CDLL('lib/utils.so')

def arcdist(lat1, lon1, lat2, lon2):
    r = 3437.905   # Earth radius in miles
    angle = np.sin(lat1)*np.sin(lat2)+np.cos(lat1)*np.cos(lat2)*np.cos(lon1-lon2)
    return r*np.arccos(angle)
    #return r*np.arccos(min(angle,1.0))

def deg2degmin(deg):
    degmin = np.floor(deg)*10000.
    min_ = (deg  - np.floor(deg ))*100*60
    degmin = degmin + min_
    return np.round(degmin).astype(np.int32)

def degmin2rad(degmin):
    if (np.abs(degmin)<10000):
        degmin = degmin*100
    m = (degmin/100.)-np.floor(degmin/10000.)*100.
    return ((degmin+(200.0/3.0)*m)/10000)*np.pi/180.0

def degmin2deg(degmin):
    if (np.abs(degmin)<10000):
        degmin = degmin*100
    min_ = (degmin/100)-np.floor(degmin/10000.)*100.
    return ((degmin+(200.0/3.0)*min_)/10000)

def deg2point (Lat, Lon, Norm=1000):
    (MAXLON,MAXLAT,MINLAT,MINLON) = (-4,70,60,-32)
# at 65lat 18lon
    lat65 = 65.*np.pi/180. ;
    x65 = (111415.13*np.cos(lat65)-94.55*np.cos(3*lat65)+0.12*np.cos(5*lat65))/60
    M65 = 7915.704456*np.log10(np.tan(np.pi/4+lat65/2)) - np.sin(lat65)*(23.110771+0.052051*(np.sin(lat65))*np.sin(lat65))
# Automatic Scaling
    lat = MAXLAT*np.pi/180
    M = 7915.704456*np.log10(np.tan(np.pi/4+lat/2))-np.sin(lat)*(23.110771+0.052051*(np.sin(lat))*np.sin(lat65))
    Diff = M-M65
    lat = MINLAT*np.pi/180
    M = 7915.704456*np.log10(np.tan(np.pi/4+lat/2))-np.sin(lat)*(23.110771+0.052051*(np.sin(lat))*np.sin(lat65))
    Diff = Diff + M65 - M
    scale = Norm/(Diff*x65)
    x65 = scale*x65
    x = []; y = []
    for i in range(len(Lat)):
        lat = Lat[i]*np.pi/180
        M = 7915.704456*np.log10(np.tan(np.pi/4+lat/2))-np.sin(lat)*(23.110771+0.052051*(np.sin(lat))*np.sin(lat65))
        Diff = M65-M
        y.append(int(Diff*x65))
        x.append(int((Lon[i]+18)*x65*60))
    return x, y

def Dijkstra_(graph, src, dest):
 #      int dijkstra(double *d, int *path, double **graph, int n, int src, int dest) {
                                   
    n = graph.shape[0]
    d_ = (ctypes.c_double)()
    
    arr = np.ascontiguousarray(graph)
    ptr_arr = (ctypes.POINTER(ctypes.c_double) * arr.shape[0])()
    for i in range(arr.shape[0]):
        ptr_arr[i] = arr[i].ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    graph_ = ctypes.cast(ptr_arr, ctypes.POINTER(ctypes.POINTER(ctypes.c_double)))
    
    path_ = (ctypes.c_int * n)()
   
    n_ = ctypes.c_int(n)
    src_ = ctypes.c_int(src)
    dest_ = ctypes.c_int(dest)
    
    lib.dijkstra.argtypes = ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.POINTER(ctypes.c_double)),ctypes.c_int,ctypes.c_int,ctypes.c_int
    lib.dijkstra(d_,path_,graph_,n_,src_,dest_)
    
    # now extract the distance and path
    p__ = np.ctypeslib.as_array(path_, shape = (n))
    print("p__ = ", p__)
    d = np.ctypeslib.as_array(d_, shape=(1))
    path = p__[:np.where(p__<0)[0][0]]
    print("path__ = ", path)
    return (d.item(),path)

def drawTour(tour, LatLonRad, Type, Amount, DistMtrx, FsbleMtrx):
    
    colors = ['b', 'g', 'c', 'm', 'y', 'k']
    c_tour = 0
    pi180 = 180.0/np.pi
    StartEnd = LatLonRad[0,:]
    # Draw Iceland
    with open('island.bin', 'rb') as f:
        landata = np.fromfile(f, dtype=np.float32)
    LandDeg = np.vstack((landata[:int(landata.size/2)],landata[int(landata.size/2):])).T
    (x,y) = deg2point(LandDeg[:,0],LandDeg[:,1],1000)
    fig,ax = plt.subplots(figsize=(10,10))
    ax.plot(x,y)
    ax.invert_yaxis()
    # Find where the tour starts, index (n-2)
    n = len(tour)
    ilast = int(tour[0]/2)
    (x_,y_) = deg2point([pi180*LatLonRad[0,0]],[-pi180*LatLonRad[0,1]],1000)
    plt.plot(x_,y_,marker = 6, color = "g") # Draw the start location
    amount = 0
    (x1,y1) = (x_,y_)
    ilast = tour[0] # location of ship should be here (start path)
    jlast = 0
    tlast = 0
    reroute = []
    # Lets draw all waypoints
    for i in range(1,len(Type)):
        if Type[i] == tWAYP:
            (x_,y_) = deg2point([pi180*LatLonRad[i,0]],[-pi180*LatLonRad[i,1]],1000)
            # the marker should be a green square
            ax.plot(x_,y_,marker = "^", color = "g")
            ax.text(x_[0],y_[0],str(i),fontsize=8)
    for i in tour[1:]: # the first two point will be (n-2,n-1) (start and end, we are painting backwards)
        # investigate if we need to reroute
        if FsbleMtrx[2*ilast+(jlast==2),2*np.abs(i)+(i<0)] == 0:
            print("connection", 2*ilast+(jlast==2),2*np.abs(i)+(i<0), "crosses land", (ilast,i))
            idx = [2*ilast+(jlast==2),2*np.abs(i)+(i<0)]
            idx.extend(2*np.where(Type == tWAYP)[0])
            #idx.extend(1+2*np.where(Type == tWAYP)[0])
            D = DistMtrx[np.ix_(idx, idx)]*FsbleMtrx[np.ix_(idx, idx)]+(1-FsbleMtrx[np.ix_(idx, idx)])*1e6
            (d,path) = Dijkstra_(D, 0, 1)
            # reverse the path
            path = path[1:-1][::-1]
            #print(path,[idx[it]/2 for it in path])
            colrs = colors[c_tour]
            lstyle = 'dotted'
            for i_ in [int(idx[it]/2) for it in path]:
                #print("plotting: ", ilast, i_)
                (x1,y1) = deg2point([pi180*LatLonRad[ilast,jlast]],[-pi180*LatLonRad[ilast,jlast+1]],1000)
                (x2,y2) = deg2point([pi180*LatLonRad[i_,0]],[-pi180*LatLonRad[i_,1]],1000)
                jlast = 0
                ilast = i_
                ax.plot([x1[0],x2[0]],[y1[0],y2[0]],color=colrs,linestyle=lstyle, linewidth=.6)
            (x1,y1) = (x2,y2)
            if (i > 0):
                (x2,y2) = deg2point([pi180*LatLonRad[i,0]],[-pi180*LatLonRad[i,1]],1000)
                ilast = i
                jlast = 2
            else:
                (x2,y2) = deg2point([pi180*LatLonRad[-i,2]],[-pi180*LatLonRad[-i,3]],1000)
                ilast = -i
                jlast = 0
            ax.plot([x1[0],x2[0]],[y1[0],y2[0]],color=colrs,linestyle=lstyle, linewidth=.6)
        if i < 0:
            if Type[-i] != tPORT and Type[-i] != tWAYP:
                amount += Amount[-i]
                (x1,y1) = deg2point([pi180*LatLonRad[ilast,jlast]],[-pi180*LatLonRad[ilast,jlast+1]],1000)
                (x2,y2) = deg2point([pi180*LatLonRad[-i,2]],[-pi180*LatLonRad[-i,3]],1000)
                jlast = 0
                ilast = -i
            #t = 2*(-i)+1
                colrs = colors[c_tour]
                lstyle = 'dotted'
                ax.plot([x1[0],x2[0]],[y1[0],y2[0]],color=colrs,linestyle=lstyle, linewidth=0.6)
                (x1,y1) = deg2point([pi180*LatLonRad[-i,2]],[-pi180*LatLonRad[-i,3]],1000)
                (x2,y2) = deg2point([pi180*LatLonRad[-i,0]],[-pi180*LatLonRad[-i,1]],1000)
            if Type[-i] == tPORT:
                (xtmp,ytmp) = deg2point([pi180*LatLonRad[-i,0]],[-pi180*LatLonRad[-i,1]],1000)
                # the marker should be a green square
                ax.plot(xtmp[0],ytmp[0],marker = "s", color = "y") # Draw the end location
                print("Port", i, "is be ignored")
                     
            else:
                ax.arrow(x1[0],y1[0],x2[0]-x1[0],y2[0]-y1[0], head_width=0.7, head_length=0.7, fc='g', ec='g')
        else:
            amount += Amount[i]
            (x1,y1) = deg2point([pi180*LatLonRad[ilast,jlast]],[-pi180*LatLonRad[ilast,jlast+1]],1000)
            (x2,y2) = deg2point([pi180*LatLonRad[i,0]],[-pi180*LatLonRad[i,1]],1000)
            jlast = 2
            ilast = i
            #t = 2*i
            colrs = colors[c_tour]
            lstyle = 'dotted'
            ax.plot([x1[0],x2[0]],[y1[0],y2[0]],color=colrs,linestyle=lstyle, linewidth=0.6)
            (x1,y1) = deg2point([pi180*LatLonRad[i,0]],[-pi180*LatLonRad[i,1]],1000)
            (x2,y2) = deg2point([pi180*LatLonRad[i,2]],[-pi180*LatLonRad[i,3]],1000)
            if Type[i] == tPORT:
                # the marker should be a green square
                ax.plot(x1[0],y1[0],marker = "s", color = "m") # Draw the end location
                amount = 0
            elif Type[i] == tWAYP:
                # the marker should be a green square
                ax.plot(x1[0],y1[0],marker = "*", color = "m") # Draw the end location
                amount = 0
            else:
                ax.arrow(x1[0],y1[0],x2[0]-x1[0],y2[0]-y1[0], head_width=0.7, head_length=0.7, fc='g', ec='g')
        
        #ax.arrow(x1[0],y1[0],x2[0]-x1[0],y2[0]-y1[0], head_width=0.7, head_length=0.7, fc='g', ec='g')
        ax.text(x1[0],y1[0],str(i),fontsize=8)
        #ax.text(x1[0],y1[0],str(amount),fontsize=6)
        #(x1,y1) = (x2,y2)
        #if ((1==isPort[i]) and (i != ilast)):
        #    print("Tour:", c_tour, "Amount:", amount)
        #    c_tour = c_tour+1
        #    amount = 0

        #ilast = i # keep track of last station
        #tlast = t
    if (LatLonRad[0,2] > 0):
        (x_,y_) = deg2point([pi180*LatLonRad[0,2]],[-pi180*LatLonRad[0,3]],1000)
    #print("Tour:", c_tour, "Amount:", amount)
        plt.plot(x_,y_,marker = 7, color = "r") # Draw the end location
        ax.plot([x2[0],x_[0]],[y2[0],y_[0]],color=colors[c_tour],linestyle='dotted', linewidth=0.6)
    plt.show()

def DistanceLink(Type, LatLon, StartEnd, Size, SelectedSize):
                                          
    DistrMtrx_ = (ctypes.c_double * (SelectedSize * SelectedSize * 4))()
    for i in range(SelectedSize * SelectedSize * 4):
        DistrMtrx_[i] = 0

    FsbleMtrx_ = (ctypes.c_int * (SelectedSize * SelectedSize * 4))()
    for i in range(SelectedSize * SelectedSize * 4):
        FsbleMtrx_[i] = int(0)
    
    Type_ = (ctypes.c_int * Size)()
    for i in range(Size):
        Type_[i] = int(Type[i])

    arr = np.ascontiguousarray(LatLon.T)
    ptr_arr = (ctypes.POINTER(ctypes.c_double) * arr.shape[0])()
    for i in range(arr.shape[0]):
        ptr_arr[i] = arr[i].ctypes.data_as(ctypes.POINTER(ctypes.c_double))

    LatLon_ = ctypes.cast(ptr_arr, ctypes.POINTER(ctypes.POINTER(ctypes.c_double)))
    print(len(StartEnd))
    StartEnd_ = (ctypes.c_double * len(StartEnd))()
    for i in range(len(StartEnd)):
        StartEnd_[i] = StartEnd[i]
    
    Size_ = ctypes.c_int(Size)

    SelectedSize_ = ctypes.c_int(SelectedSize)
        
    lib.DistanceLink.argtypes = ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.POINTER(ctypes.c_double)),ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.c_int
    lib.DistanceLink(DistrMtrx_,FsbleMtrx_,Type_,LatLon_,StartEnd_,Size_,SelectedSize_)
    
    # now extract the tour
    DistMtrx = np.ctypeslib.as_array(DistrMtrx_, shape = ((SelectedSize*2*SelectedSize*2)))
    FsbleMtrx = np.ctypeslib.as_array(FsbleMtrx_, shape = ((SelectedSize*2*SelectedSize*2)))
    
    return (DistMtrx.reshape((SelectedSize*2,SelectedSize*2)), FsbleMtrx.reshape((SelectedSize*2,SelectedSize*2)))

def readDat(fname, ship_name = 'Bjarni Sæmundsson'):
    
    ship_name = '"'+ship_name+'"'
    print("reading file: ", fname)
    lines = open(fname, encoding="utf8").readlines()
    print("the number of line is:", len(lines), "searching for", ship_name)
    Type = []; Fixed = []; LatLon = []; Name = []; Rotated = []; Amount = []; Tour = []; ExtraTime = []
    found_ship = False
    ShipCap = 0
    k = 0
    tag = 'ALL'
    for i in range(len(lines)):
        leline = re.findall(r'"[^"]*"|\S+', lines[i])

        #print(leline)
        if len(leline) <= 1:
            break
        if tag == 'ALL':
            se = leline[0]
        elif tag == 'WAYPONLY' and leline[0] == "WAYP":
            se = leline[0]
        else:
            se = "IGNORE"
        if (se == 'PORT') and found_ship:
            if leline[4] == '1':
                data = np.array(leline[1:3]).astype(np.float64)
                Type.append(tPORT)
                LatLon.append(np.concatenate((data[:2],data[:2])))
                Fixed.append(False)
                Rotated.append(False)
                Amount.append(0)
                Name.append(leline[3])
                ExtraTime.append(0)
                if found_ship:
                    Tour.append(k)
                else:
                    Tour.append(-k)
                k = k + 1 
        elif (se == 'WAYP'):
            if leline[3] != '-1':
                Type.append(tWAYP)
                data = np.array(leline[1:3]).astype(np.float64)
                LatLon.append(np.concatenate((data[:2],data[:2])))
                Fixed.append(False)
                Rotated.append(False)
                Amount.append(0)
                ExtraTime.append(0)
                Name.append("Wayp")
                if found_ship:
                    Tour.append(k)
                else:
                    Tour.append(-k)
                k = k + 1 
        elif (se == 'BOAT'):
            if found_ship == True:
                tag = 'WAYPONLY'
            elif leline[12] == ship_name:
                data = np.array(leline[1:12]).astype(np.float64)
                found_ship = True
                ShipCap = data[4]
                Type.append(tSHIP)
                LatLon.append(data[:4])
                Fixed.append(False)
                Rotated.append(False)
                Name.append(ship_name)  
                Amount.append(0)   # this should be the initial amount of cargo
                ExtraTime.append(0)
                print("found ship", ship_name, "at line", i)
                Tour.append(k)
                k = k + 1 
            else:
                found_ship = False
        elif (se == 'STAT') and found_ship:
            data = np.array(leline[1:10]).astype(np.float64).astype(np.int32)
            if data[2] != 5:
                Type.append(tSTAT)
                LatLon.append(data[3:7])
                Fixed.append(data[2]==2)
                Rotated.append(data[2]==1)
                Amount.append(data[7])
                ExtraTime.append(data[8])
                Name.append(str(abs(data[0]))+" "+str(abs(data[1])))
                if data[0]<0:
                    Tour.append(-k)
                else:
                    Tour.append(k)
                k = k + 1 
    LatLon = np.array(LatLon)
    for i in range(LatLon.shape[0]):
        for j in range(LatLon.shape[1]):
            LatLon[i,j] = degmin2rad(LatLon[i,j])
    Fixed = np.array(Fixed)
    Rotated = np.array(Rotated)
    Amount = np.array(Amount)
    ExtraTime = np.array(ExtraTime)
    Type = np.array(Type)
    assert(found_ship)
    return (Tour, Type, Amount, Fixed, LatLon, Name, Rotated, ShipCap, ExtraTime)

def writeDat(fname, Tour, mode, Type, Amount, Fixed, LatLon, Name, ExtraTime, ship_name):
    pi180 = 180.0/np.pi
# Using with statement for automatic file handling
    lasttype = -1
    with open(fname, 'w') as file:
        for ii in Tour:
            i = np.abs(ii)
            if Type[i] == tSHIP:
            # SHIP 663381 224128 25000 10 5 30 255 153 153 " Bjarni Sæmundsson "
                print("BOAT", Type[i], ii, Tour)
                line = "BOAT " + str(deg2degmin(LatLon[i,0]*pi180)) + " " + str(deg2degmin(LatLon[i,1]*pi180)) + " " + str(deg2degmin(LatLon[i,2]*pi180)) + " " + str(deg2degmin(LatLon[i,3]*pi180)) + " " + str(Amount[i]) + " 10 5 30 255 153 153 " + '"' + ship_name + '"'
            elif Type[i] == tPORT:
            # PORT 661066 185279 "Siglufjörður" 1 #
                line = "PORT " + str(deg2degmin(LatLon[i,0]*pi180)) + " " + str(deg2degmin(LatLon[i,1]*pi180)) + " " + Name[i] + " 1" 
            elif Type[i] == tSTAT:
                # STAT 671 5 -3 663615 215451 663716 214461 2215 #
                leline = Name[i].split()
                if ii < 0 and Fixed[i] == True:
                    sr = 3
                elif ii <= 0:
                    sr = 1
                elif Fixed[i] == True:
                    sr = 2
                else:
                    sr = 0
                line = "STAT " + leline[0] + " " + leline[1] + " " + str(sr) + " " + str(deg2degmin(LatLon[i,0]*pi180)) + " " + str(deg2degmin(LatLon[i,1]*pi180)) + " " + str(deg2degmin(LatLon[i,2]*pi180)) + " " + str(deg2degmin(LatLon[i,3]*pi180)) + " " + str(Amount[i]) + " " + str(ExtraTime[i]) + " # "    
            if ((lasttype == tPORT and Type[i] == tPORT) == False) and ((Type[i] == tPORT and mode == "ea" and ii < 0) == False):
                file.write(line + "\n")  # Adding a newline character to each line
            lasttype = Type[i]
        # the remaining ports not used
        therest = set(list(range(len(Type)))) - set(abs(Tour))
        for i in range(len(Type)):
            if Type[i] == tPORT:
                line = "PORT " + str(deg2degmin(LatLon[i,0]*pi180)) + " " + str(deg2degmin(LatLon[i,1]*pi180)) + " " + Name[i] + " 0"       
                file.write(line + "\n")
        # all way points used and not used
        for i in therest:
            if Type[i] == tWAYP:
                line = "WAYP " + str(deg2degmin(LatLon[i,0]*pi180)) + " " + str(deg2degmin(LatLon[i,1]*pi180)) + " 1" 
                file.write(line + "\n")

