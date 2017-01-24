######################################################################
# Author: Andrew White, Department of Atmospheric Science,           #
#         University of Alabama in Huntsville                        #
#                                                                    #
# Python class SkewTobj, which is used to plot a vertical profile of #
# environmental temp, dew point temp, and parcel temp on a           # 
# skewT-log P plot                                                   #
#                                                                    #
######################################################################

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from matplotlib.ticker import LogLocator
import time

class SkewTobj:
    
    def __init__(self, temp = None, pressure = None, Z = None, qv = None, td = None, parcel = None):
        
        #Set Global Constants
        self.g = 9.81            #gravity  [m/s^2]
        self.rd = 287.04         #dry air gas constant [J / (kg K)]
        self.cp = 1004.          #specific heat of air at constant pressure   [J / (kg K)]
        self.rv = 461.           #moist air gas constant [J / (kg K)]
        self.Ep = 18.016/29.87   #mass vapor over mass dry air
        
        #Check if Temperature, Pressure and Mixing Ratio are provided
        if (temp is not None and pressure is not None and qv is not None):
            #Guess input temperature units (Celsius or Kelvin)
            #Temperature should be in C
            if (np.any(temp > 200.)):
                print("Input temperature in Kelvin --> converting to Celsius")
                temp -= 273.15
            #Guess input pressure units (Pa of hPa)
            #Pressure should be in hPa
            if (np.any(pressure > 10000.)):
                print("Input pressure in Pa --> converting to hPa")
                pressure /= 100.
            #Guess input mixing ratio units (g/kg or kg/kg)
            #Mixing ratio should be in kg/kg
            if (np.any(qv > 5.)):
                print("Input mixing ratio in g/kg --> converting to kg/kg")
                qv /= 1000.
            #Guess input dew point temperature units (Celsius or Kelvin)
            #Should be in C
            if (td is not None):
                if (np.any(td > 200.)):
                    print("Input dew point temperature in Kelvin --> converting to Celsius")
                    td -= 273.15
            self.RunProgram(temp,pressure,qv,Z,td,parcel)
        else:
            print("Please provide temperature, pressure and mixing ratio")

    #Call the routines if necessary input data is provided
    def RunProgram(self, t, p, q, Z = None, td = None, parcel = None):
        
        #Make sure mixing ratio values are positive
        q[np.where(q < 0.0)] = 0.0
        
        #Calculate theta
        self.theta = (t+273.15) * (1000./p)**(self.rd/self.cp)
        
        #
        self.Z = Z
        self.press = p        
 
        #Call functions
        #Skew-T lines
        self.MixingRatioLines()
        self.PotentialTempLines()
        self.TemperatureLines()
        self.MoistAdiabatLines()
        
        #Vertical Profile
        self.EnvTemp(t,p)
        self.EnvVTemp(t,p,q)
        #If dew point is not provided calculate it
        if (td is None):
            self.DewTemp(t,p,q)
        else:
            self.tdew = td
            self.x_dew, self.y_dew = self.RotatePoints(td,p)
        #Determine requested parcel
        if (parcel is None):
            #Default to ML
            parcel = "ML"
        if (parcel == "SB"):
            self.Surface(t, p, q, self.tdew)
        elif (parcel == "ML"):
            self.MixedLayer(t, p, q, self.tdew)
        elif (parcel == "MU"):
            self.MostUnstable(t, p, q, self.tdew)
        else:
            print("Input parcel name not recognized: "+parcel)
            print("Options are SB, ML and MU")
            print("Switching to default...ML")
            self.MixedLayer(t, p, q, self.tdew)
            
        self.ParcelTemp(p, q)
        self.CreatePlot()  
        
    #Mixing Ratio Lines
    def MixingRatioLines(self):
        
        q = np.array((1,2,3,5,8,12,20,40))/1000.
        p_array = np.arange(550,1100,10)
        t = np.zeros((len(q),len(p_array)))
        for i in range(len(q)):
            A = np.log((p_array * q[i] / ((0.622 + q[i]))) * (1./6.112))
            t[i,:] = 243.5 * A / (17.67 - A)
        p = np.tile(p_array, (len(q),1))
        self.x_mr, self.y_mr = self.RotatePoints(t,p)          
        
    #Potential Temperature Lines
    def PotentialTempLines(self):
        
        theta = np.arange(-50,100,20)
        t_array = np.arange(-130,50,1)
        p = np.zeros((len(theta),len(t_array)))
        for i in range(len(theta)):
            p[i,:] = 1000. * ((t_array+273.15)/(theta[i]+273.15))**(self.cp/self.rd)
        t = np.tile(t_array, (len(theta),1))          
        self.x_theta, self.y_theta = self.RotatePoints(t,p) 

    #Temperature Lines
    def TemperatureLines(self):
        
        t_array = np.arange(-100,60,10)
        p_array = np.arange(50,1150,50)
        t = np.tile(np.array([t_array]).transpose(), (1, len(p_array)))
        p = np.tile(p_array, (len(t_array),1))
        self.x_temp, self.y_temp = self.RotatePoints(t,p) 
 
    #Theta - e Lines
    def MoistAdiabatLines(self):
        
        t_array = np.arange(0,50,10)
        vpsat = self.VaporPressure(t_array)
        qsat = (0.622*vpsat)/(1000. - vpsat)
        p_array = np.arange(1000,40,-10)
        theta = (t_array+273.15) * (1000./p_array[1])**(self.rd/self.cp)
        t = np.zeros((len(t_array),len(p_array)))
        t[:,0] = t_array + 273.15
        for k in range(1,len(p_array)):
            theta, qsat, t[:,k] = self.TParcel(p_array[k],qsat,theta)          
        p = np.tile(p_array, (len(t_array),1))             
        self.x_thetae, self.y_thetae = self.RotatePoints(t - 273.15,p) 

    #Environmental Temperature
    def EnvTemp(self, t, p):
        
        self.x_env, self.y_env = self.RotatePoints(t,p) 

    #Environmental Temperature
    def DewTemp(self, t, p, q):

        vp = (q*p)/(q + self.Ep)
        self.tdew = (243.5 * np.log(vp/6.112)) / (17.67 - np.log(vp/6.112))
        #Make Dew point correction
        # In saturated condition td calculation could lead to td > t
        ind = np.where(self.tdew > t)
        self.tdew[ind] = t[ind]
        self.x_dew, self.y_dew = self.RotatePoints(self.tdew,p) 
        
    #Environmental Virtual Temperature
    def EnvVTemp(self, t, p, q):

        self.tv = (t + 273.15) * (1. + 0.608 * q) - 273.15
        self.x_envtv, self.y_envtv = self.RotatePoints(self.tv,p) 
        
    #Define Surface Based Parcel
    def Surface(self, t, p, q, td):

        self.t_parcel = t[0]
        self.p_parcel = p[0]
        self.q_parcel = q[0]
        self.td_parcel = td[0]
        self.theta_parcel = self.theta[0]
        
    #Define Mixed Layer Parcel (mean lowest 100 mb parcel)
    def MixedLayer(self, t, p, q, td):
        
        #Determine psfc - 100mb
        minP = p[0] - 100.
        diff = p - minP
        ind = np.where(diff > 0)
        self.t_parcel = np.sum(t[ind]) / len(ind[0])
        self.td_parcel = np.sum(td[ind]) / len(ind[0])
        self.q_parcel = np.sum(q[ind]) / len(ind[0])
        self.theta_parcel = np.sum(self.theta[ind]) / len(ind[0])
        self.p_parcel = p[0] 
        
    #Define Most Unstable Parcel (Max Theta-e in lowest 300 mb)
    def MostUnstable(self, t, p, q, td):

        #Determine psfc - 300mb
        minP = p[0] - 300.
        diff = p - minP
        ind = np.where(diff > 0)
        
        #Determine max theta-e
        vp = self.VaporPressure(td[ind])
        t_lcl = self.TempLCL(t[ind]+273.15,td[ind])
        thetae = self.theta[ind] * np.exp((3.376/t_lcl - 0.00254)*1000*q[ind]*(1. + 0.81 * q[ind]))
        indmax = np.where(thetae == np.amax(thetae))
        
        #Define parcel        
        self.t_parcel = t[indmax]
        self.q_parcel = q[indmax]
        self.theta_parcel = self.theta[indmax]
        self.td_parcel = td[indmax]
        self.p_parcel = p[0]
        
    #Lifted Parcel Temperature
    def ParcelTemp(self, p, q):
        
        #Condition is mostly for surface based parcels
        #if (self.td_parcel == self.t_parcel):
        #    tlcl = self.t_parcel + 273.15
        #    plcl = self.p_parcel
        #else:
        #    tlcl = self.TempLCL(self.t_parcel,self.td_parcel)
        #    plcl = self.PressLCL(tlcl,self.theta_parcel)
        
        #Calculate Saturation mixing ratio along constant potential temperature
        t_pt = self.theta_parcel * (p/1000.)**(self.rd/self.cp) - 273.15
        vpsat = 6.112*np.exp(17.67*t_pt/(243.5+t_pt))
        qsat = self.Ep*vpsat / (p - vpsat)
            
        theta_lcl = self.theta_parcel
        q_lcl = self.q_parcel
        t_par = np.zeros(len(p))
        t_parv = np.zeros(len(p))
        
        for k in range(len(qsat)):
            if (qsat[k] > self.q_parcel):
                #Dry Lift
                t_par[k] = self.theta_parcel * (p[k]/1000.)**(self.rd/self.cp)
                t_parv[k] = t_par[k] * (1. + 0.61*q_lcl)
            else:
                #Wet Lift
                theta_lcl, q_lcl, t_par[k] = self.TParcel(p[k],q_lcl,theta_lcl) 
                #q_lcl is updated to be the saturation mixing ratio at t_par
                t_parv[k] = t_par[k] * (1. + 0.61*q_lcl)
        #self.x_par, self.y_par = self.RotatePoints(t_par-273.15,p)
        self.x_parv, self.y_parv = self.RotatePoints(t_parv-273.15,p)
        
    #Rotate the points 
    def RotatePoints(self, x_in, y_in):
        #Rotational matrix
        angle = np.pi/1.065
        rot = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])

        #Rotation Stuff
        x = 0.
        y = np.log(1000.)*-self.rd
        d1 = np.array([[x],[y]])
        V1 = np.dot(rot,d1)
        B1 = np.linspace(d1[0],V1[0],100)
        B2 = np.linspace(d1[1],V1[1],100)
        p = np.polyfit(B1,B2,1)
    
        #Skew-T y-axis
        y_out = -self.rd*np.log(y_in) 
        
        #Skew-T x-axis
        B = (x_in + (-y/p[0]))*p[0]
        x_out = (y_out+B)/p[0]
        
        return x_out, y_out

    #Rotate the points 
    def CreatePlot(self):
        
        self.fig = plt.figure(figsize=(8, 7))
        #fig.canvas.set_window_title('Skew-T')
        self.ax = self.fig.add_subplot(111)

        #Plot Mixing Ratio Lines
        dims_mr = self.x_mr.shape
        for i in range(dims_mr[0]):
            plt.plot(self.x_mr[i,:],self.y_mr[i,:], 'k:')

        #Plot Potential Temperature Lines
        dims_theta = self.x_theta.shape
        for i in range(dims_theta[0]):
            plt.plot(self.x_theta[i,:],self.y_theta[i,:], 'k:')

        #Plot Potential Temperature Lines
        dims_temp = self.x_temp.shape
        for i in range(dims_temp[0]):
            plt.plot(self.x_temp[i,:],self.y_temp[i,:], 'k:')   

        #Plot Moist Adiabat Lines
        dims_thetae = self.x_thetae.shape
        for i in range(dims_thetae[0]):
            plt.plot(self.x_thetae[i,:],self.y_thetae[i,:], 'k:') 
        
        #Plot the Environmental Temperture
        plt.plot(self.x_env,self.y_env, 'r', linewidth=3.0)

        #Plot the Environmental Virtual Temperture
        plt.plot(self.x_envtv,self.y_envtv, 'r:', linewidth=3.0)
 
        #Plot the Dew Point Temperture
        plt.plot(self.x_dew,self.y_dew, 'g', linewidth=3.0)

        #Plot the Parcel Path
        #plt.plot(self.x_par,self.y_par, 'b:', linewidth=2.0)
        
        #Plot the Parcel Path -- virtual temperature
        plt.plot(self.x_parv,self.y_parv, 'b', linewidth=2.0)
    
        #Set up pressure y_axis
        p_ticks = np.linspace(100, 1000, 10)
        plt.ylim(-self.rd*np.log(1000.),-self.rd*np.log(100.))
        self.ax.set_yticks(-self.rd*np.log(p_ticks))
        labels = self.ax.set_yticklabels(p_ticks)
        #ax.set_yscale('log')
        #ax.set_ylim(self.rd*np.log(1000.),self.rd*np.log(self.press.min()))
        #subs = [1,2,3,4,5,6,7,8,9,10]
        #loc = LogLocator(subs=self.rd*np.log(subs))
        #ax.yaxis.set_major_locator(loc)
        #fmt = FormatStrFormatter("%g")
        #ax.yaxis.set_major_formatter(fmt)
        plt.xlim(-50.,50)
        self.ax.set_xticks(np.arange(-50,51,10))
        self.ax.yaxis.grid(True)

        #Axis labels
        #plt.ylabel('Pressure [hPa]')
        #plt.xlabel('Temperature [$^o$C]')
        self.ax.set_ylabel('Pressure [hPa]')        

        #Change background color
        #ax.set_axis_bgcolor('black')
        
        #Set up second Height axis
        ax2 = self.ax.twinx()
        h_ticks = -8.0 * np.log(p_ticks/1000.)
        ax2.set_yticks(abs(h_ticks))
        labels = ax2.set_yticklabels(abs(h_ticks))
        ax2.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        #mhgt = self.Z.min()*np.log(1000./self.press.max())
        #ax2.set_ylim(mhgt, self.Z.max())
        ax2.set_ylabel('Height [km]')
        
        #plt.show()
        #plt.close()
        
    #Calculate Vapor Pressure from Bolton (1980)
    def VaporPressure(self, t):
        
        vp = 6.112 * np.exp(17.67*t/(243.5 + t))
        return vp

    #Calculate LCL temperature
    def TempLCL(self, t, td):
        
        vp = self.VaporPressure(td)
        tlcl = (2840./(3.5*np.log(t+273.15)-np.log(vp)-4.805))+55.
        return tlcl

    #Calculate LCL pressure
    def PressLCL(self, tlcl, theta):
        
        #Determine P at t_lcl -- exact based on potential temperature
        plcl = 1000. / (np.power((theta / tlcl),(1./(self.rd/self.cp))))
        return plcl
    
    #Moist Parcel Path
    def TParcel(self, p, w, theta):
    
        dims = p.shape
        if (len(dims) == 0):
            sz = 1
        elif (len(dims) == 1):
            sz = dims[0]
        else:
            sz = dims[1]
        
        kpa = self.rd/self.cp
        L = 2.5e6
        p0 = 1000.
        
        dwthres = 0.000000001
        dwf = np.zeros(sz) + 1./3.
        
        tk = theta * (p/p0)**kpa
        vp = 6.112*np.exp(17.67*(tk-273.15)/(243.5+(tk-273.15)))
        ws = 0.622*vp / (p - vp)
        dw = dwf * (ws - w)
                       
        while(np.any(abs(dw) > dwthres)):
            
            #Set old values for fail safe
            dwold = dw
            theta_old = theta
            w_old = w
            tk_old = tk
            ws_old = ws
            
            #Calculate new values
            dw = dwf * (ws - w)
            theta = theta - (dw*L*theta) / (1004.*tk)
            w = w + dw
            tk = theta * (p/p0)**kpa
            vp = 6.112*np.exp(17.67*(tk-273.15)/(243.5+(tk-273.15)))
            ws = 0.622*vp / (p-vp)
            
            #Check to make sure ws is less than the guess w
            #If so reduce the iterator and recalculate
            if (np.any(ws > w)):
                dwf = 0.5 * dwf
                theta = theta_old
                w = w_old
                tk = tk_old
                ws = ws_old
    
        tv = (theta*(p/p0)**kpa)
        return theta, w, tv           
