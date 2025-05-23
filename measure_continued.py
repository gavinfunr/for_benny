#HOW TO RUN IN LAB
#To run this program on the MSI Laptop in Dr. Hanna's lab:
# 1. Open the Lab_Python.py file found in the folder Lab-Software(Program) inside of VSCode. 
# 2. The program's code will open and so should a gitbash terminal, if a gitbash terminal does not open:
#     Click Terminal>New Terminal and a Terminal will open.
#     Then click the down arrow next to the + , and select "Git Bash".
#     If you see a green "lapto@MSI" next to a purple "MINGW64" next to a yellow ~, then step 2 is done
# 3. Type "cd Desktop/Lab_Software" to enter the correct folder.
# 4. When ready to start the GUI, type py -m Lab_Software.py and enter, then wait.

#------------------------------------------------
#Python script to run lab instruments and form GUI
#Version 1.0
#for questions contact Gavin Fisher at GavinFisherProfessional@gmail.com
#                  or  Sam Hutton   at rhutton@unr.edu
#------------------------------------------------

#-------------------
#TO-DO:
#fix voltage ranges on nidaq
#handle computation for run time based on acc, vel
#finish gui
#-------------------

#this file uses the thorlabs_apt library hosted at https://github.com/qpit/thorlabs_apt/blob/master/thorlabs_apt/core.py
#               the nidaqmx library at https://github.com/ni/nidaqmx-python/tree/master
#               and dearpygui at https://github.com/hoffstadt/DearPyGui
#as well as pandas, matplotlib.pyplot, datetime, os, and cytypes.

# import faulthandler
# faulthandler.enable()

import thorlabs_apt as apt
import dearpygui.dearpygui as dpg
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
from nidaqmx.constants import (AcquisitionType)
import nidaqmx.system
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import os
import collections
import threading
from datetime import datetime
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import getpass
matplotlib.use('agg')

HWTYPE_LTS300 = 42 # LTS300/LTS150 Long Travel Integrated Driver/Stages

#motor configs gives device info in tuples
motor_configs = apt.list_available_devices()
motor = apt.Motor(motor_configs[0][1]) #establishes communication with LTS motor, sets class at motor.
MotorPos = motor.position
backlash = 0
current_cycle = 0
motor.backlash_distance=backlash



#code for realtime graphs

# global liveplot
# liveplot = True
# Can use collections if you only need the last 100 samples

class Object(object):
    pass

program_parameters = Object()
program_parameters.save = False
program_parameters.liveplot = True
program_parameters.is_sampling = False
program_parameters.move_forward = False
program_parameters.move_backward = False
program_parameters.position_get = []
emailsend = False

global sample
global data_z
global data_y  
global data_x  
nsamples = 200

data_y = collections.deque([0.0],maxlen=nsamples)
data_x = collections.deque([0.0],maxlen=nsamples)
data_z = collections.deque([0.0],maxlen=nsamples)


dpg.create_context()
# # dpg.create_context()
# # dpg.set_value('series_tag', [list(data_x), list(data_y)])          
# # dpg.fit_axis_data('x_axis')
# # dpg.set_axis_limits('y_axis', ymin=-1, ymax=10
# #                                 )
# # dpg.set_value('series_tag2', [list(data_x), list(data_z)])          
# # dpg.fit_axis_data('x_axis2')
# # dpg.fit_axis_data('z_axis') 

def update_data():
   
    sample = 1

    data_y = collections.deque([0.0],maxlen=nsamples)
    data_x = collections.deque([0.0],maxlen=nsamples)
    data_z = collections.deque([0.0],maxlen=nsamples)

    while program_parameters.liveplot:                   
        with nidaqmx.Task() as liveplot_channel:
            liveplot_channel.ai_channels.add_ai_voltage_chan("Dev1/ai2", min_val=0, max_val=10)
          
          
            liveplot_channel.ai_channels.add_ai_voltage_chan("Dev1/ai4", min_val=-1, max_val=1.95)
            liveplot_channel.timing.cfg_samp_clk_timing(10000)  #frequncy of sample rate
            sensor_data_live = liveplot_channel.read(number_of_samples_per_channel=1)


                    # Get new data sample. Note we need both x and y values
                    # if we want a meaningful axis unit
            INDUCTOR_Sensor_data = sensor_data_live[0]
            LVIT_Sensor_data = sensor_data_live[1]
            # dum_sample = list(range(1,sample))
            data_x.append(sample)
            data_y.append(LVIT_Sensor_data[0])
            data_z.append(INDUCTOR_Sensor_data[0])
            
           
          
            dpg.set_value('series_tag', [list(data_x), list(data_y)])          
            dpg.fit_axis_data('x_axis')
            dpg.fit_axis_data('y_axis')
            #dpg.set_axis_limits('y_axis', ymin=-1, ymax=10)
            # print('after')
                                       
            dpg.set_value('series_tag2', [list(data_x), list(data_z)])          
            dpg.fit_axis_data('x_axis2')
            dpg.fit_axis_data('z_axis')
            sample=sample+1
                
            

def button_callback(sender, app_data, user_data):
    # Unpack the user_data that is currently associated with the button
    #   global state    
    #   state, enabled_theme, disabled_theme = user_data
  # Flip the state
  program_parameters.save = not program_parameters.save
    #       state = not state
  # Apply the appropriate theme
  dpg.bind_item_theme(sender, item_theme_GREEN if program_parameters.save is True else item_theme_RED)
  # Update the user_data associated with the button
  dpg.set_item_user_data(sender, (program_parameters.save, item_theme_GREEN, item_theme_RED,))
#   return state

# def position_from_time_and_frequency(freq, tot_time):
#     S = linspace(0,freq*tot_time)
#     return (v_get^2/a/get)+v_get*(S/freq)



#FUNCTIONS
def popup_funct_home(sender):#Function to home the stage.
    dpg.configure_item("modal_id", show=False)
    motor.move_home() #HOMES MOTOR
    dpg.set_value("location", 0 )

def data_collection(numbersamples, frequency):
        program_parameters.is_sampling = True
        task = nidaqmx.Task(new_task_name='task')
        task.ai_channels.add_ai_voltage_chan("Dev1/ai2", terminal_config=TerminalConfiguration(-1), min_val=0,max_val=10) ##initialize data acquisition task. Dev1 is the name of the DAQ, AV2 is the channel the induc is connected to.
        task.ai_channels.add_ai_voltage_chan("Dev1/ai4", terminal_config=TerminalConfiguration(-1), min_val=-1,max_val=1.95)#For more info on TermConfig see: https://knowledge.ni.com/KnowledgeArticleDetails?id=kA00Z0000019QRZSA2&l=en-US
        
        #      and https://www.ni.com/en-us/shop/data-acquisition/sensor-fundamentals/measuring-direct-current-dc-voltage.html
        # print(list(task.ai_channels))
        task.timing.cfg_samp_clk_timing(rate=frequency, sample_mode=AcquisitionType.FINITE, samps_per_chan=numbersamples)
        task.start()
        pos_thread = threading.Thread(target=pos_get)
        pos_thread.start()
        sensor_data2 = task.read(number_of_samples_per_channel = numbersamples,timeout=nidaqmx.constants.WAIT_INFINITELY)
        print(f"number of samples is {numbersamples}")
        print(len(sensor_data2))
        program_parameters.is_sampling = False
        task.stop()
        task.close()
        return sensor_data2

def png_output(sensor_data,numsamples,frequency):
    pos = pos_get(numsamples,frequency)
    folder_path = "C:/Users/lapto/Desktop/lab_program/data_output"
    os.makedirs(folder_path, exist_ok=True)  #only makes a new folder if there isnt one named 'folder_path'
    posdf = pd.DataFrame(pos)
    df = pd.DataFrame(sensor_data)  
    df_induc = df.iloc[0]
    df_LVIT = df.iloc[1]                         

    plt.figure(1) #Plots and saves the induc graph
    plt.xlabel('# of samples'), plt.ylabel('Induction Sensor Voltage'), plt.ylim(0,10)
    plt.plot(df_induc, c = 'b')  #This section creates the Png of the induction sensor graph. c is the color, s is the size of the points
    png_name = datetime.now().strftime("%B_%d_Time_%I-%M-%S")    #Create the file name. Spaces, word without quotes seem to work, see 'time'.
    file_name = f'Induc_{png_name}.png' 
    file_path = os.path.join(folder_path,file_name)
    plt.savefig(file_path, dpi=1000)

    #print(df_LVIT)
    plt.figure(2) #plots and saves LVIT graph
    plt.xlabel('# of samples'), plt.ylabel('LVIT Volts'), plt.ylim(0,10)
    plt.plot(df_LVIT, c = 'b')  
    file_name = f'LVIT_{png_name}.png' 
    file_path = os.path.join(folder_path,file_name)
    plt.savefig(file_path, dpi=1000)

    plt.figure(3) #plots and saves position graph
    plt.xlabel('# of samples'), plt.ylabel('Position in (units?)')
    plt.plot(posdf, c = 'b')
    file_name = f'Position_{png_name}.png' 
    file_path = os.path.join(folder_path,file_name)
    plt.savefig(file_path, dpi=1000)

    plt.close()

def csv_output(sensor_data2,pos):
    if motor.is_in_motion==False:
        df = pd.DataFrame(sensor_data2)
        df1 = df.transpose()
        df2 = pd.concat([df1,pd.DataFrame(pos)], axis=1)
        names = ["Induction","LVIT","Position"]
        df2.columns = names
        folder_path = "C:/Users/lapto/Desktop/lab_program/data_output/"
        csv_name = datetime.now().strftime("%B_%d_Time_%I-%M-%S")    #Create the file name. Spaces, word without quotes seem to work, ex: 'time'.
        file_name = f'Csv_{csv_name}.csv' 
        file_path = os.path.join(folder_path,file_name)
        df2.to_csv(file_path)
        plt.plot(df2)
        plt.savefig("test.png")
        


def pos_get():
    program_parameters.position_get = []
    while program_parameters.is_sampling is True:
       #print('dentro de posget')
       program_parameters.position_get.append(motor.position)  
    # return pos

def positionupdate():
    while True:
        LTSpos = motor.position
        #print(LTSpos)
        dpg.set_value("location", LTSpos)

def motor_move_to():                                          # start movement of motor for 1 run
    Position_Get = dpg.get_value(position)
    motor.move_to(Position_Get)  #command that gets sent to LTS, initaites movement

def motor_move_cycle(): # start movement of motor for cycle function
    target_position = dpg.get_value(target_position_input)
    motor.move_to(target_position)  

def motor_move_back():  #start movement of motor for cycle function coming back to initial position
    initial_position = dpg.get_value(initial_position_input)
    motor.move_to(initial_position)  

motor_to_thread = threading.Thread(target=motor_move_to)
motor_to_cycle_thread = threading.Thread(target=motor_move_cycle)
motor_back_thread = threading.Thread(target=motor_move_back)

def run_function(sender):  #pulls input parameters and assigns them variables when run button is clicked  
    
    Accel_Get = dpg.get_value(accel)  #These 4 lines fetch the  our inputs from the GUI and assign them to varibles
    Velo_Get = dpg.get_value(velo)
    Position_Get = dpg.get_value(position)
    frequency = dpg.get_value(samplerate)  

    MotorPos = motor.position    #These 10 lines calculate run time and total number of samples with mydac
    dP = abs(MotorPos-Position_Get)
    dT = 2*(Velo_Get/Accel_Get) + (dP/Velo_Get) - (Velo_Get/(Accel_Get))+2*(backlash/Velo_Get)+0.01

    
    program_parameters.number_samples = int(dT * frequency)
    
    print(f"Time to run in Sec: {dT}")
    print(f"Number of samples: {program_parameters.number_samples}")

    print(Position_Get)
    print(Accel_Get)
    print(Velo_Get)
    motor.set_velocity_parameters(0,Accel_Get,Velo_Get)  #inputs min velocity (0), acceleration and max velocity
    motor.move_to(Position_Get)  #command that gets sent to LTS, initaites movement


 
    #print(Position_Get)
    # dpg.set_value("location", Position_Get)
    
    if program_parameters.save == True:  #from save toggle button on GUI, if True code pauses live sampling and calls the function data collection to sampl
    
        output_constant_voltage_for_duration("Dev1/ao0", voltage=5, duration=0.1)
        
        program_parameters.is_sampling = True
        program_parameters.liveplot = False
        time.sleep(.1)
        numbersamples = program_parameters.number_samples
   
        shared_sensor_data = []
        data_thread = threading.Thread(target=lambda: shared_sensor_data.extend(data_collection(numbersamples, frequency)))
        data_thread.start()
        print('moving to objective')
        motor.move_to(Position_Get)
        time.sleep(0.1)
        while motor.is_in_motion:
          #print('in first while')
           time.sleep(.01)
        
        #sensor_data2 = data_collection(numbersamples, frequency) # function that samples Inductor and LVIT 

        #restarts while loop allowing live plots to function
        # print(sensor_data2)
        
        # posdf = pos_get()
        # png_output(sensor_data2,numsamples,frequency)
        while program_parameters.is_sampling is True:
           time.sleep(0.01)
                  #print('in third while')
        output_constant_voltage_for_duration("Dev1/ao0", voltage=5, duration=0.1) 
        time.sleep(0.5)
        csv_output(shared_sensor_data, program_parameters.position_get)

        program_parameters.liveplot = True 
        thread = threading.Thread(target=update_data) #restarts thread application for live plots
        thread.start()






def execute_cycles(sender):
    current_cycle = 0
    number_of_cycles = int(dpg.get_value(cycles_input))
    
    initial_position = dpg.get_value(initial_position_input)
    target_position = dpg.get_value(target_position_input)

    Accel_Get = dpg.get_value(accel)  #These 4 lines fetch the  our inputs from the GUI and assign them to varibles
    Velo_Get = dpg.get_value(velo)
    Position_Get = target_position
    frequency = dpg.get_value(samplerate)  
    MotorPos = motor.position    #These 10 lines calculate run time and total number of samples with mydac
    dP1 = abs(MotorPos-Position_Get)
    dP2 = abs(initial_position-target_position)
    dT1 = 2*(Velo_Get/Accel_Get) + (dP1/Velo_Get) - (Velo_Get/(Accel_Get)) + 2*(motor.backlash_distance/Velo_Get)
    dT2 = 2*(Velo_Get/Accel_Get) + (dP2/Velo_Get) - (Velo_Get/(Accel_Get)) + 2*(motor.backlash_distance/Velo_Get)+0.01
    dT = dT1+dT2
    print(f"Time to run in min: {(dT/60)*number_of_cycles}")
    print(f"Time to run in min: {(dT1/60)*number_of_cycles}")
    print(f"Time to run in min: {(dT2/60)*number_of_cycles}")
    acceleration = dpg.get_value(accel)
    velocity = dpg.get_value(velo)
    motor.set_velocity_parameters(0, acceleration, velocity)  
    program_parameters.number_samples = int(dT * frequency)
    print('Num Samples Calculated')
    
    for cycle in range(number_of_cycles):
                print(f"current cyle: {cycle+1}")
                
                current_cycle=current_cycle+1
                dpg.set_value(cycles_count,current_cycle)
                motor.backlash_distance=backlash
               # motor.move_to(target_position)
                output_constant_voltage_for_duration("Dev1/ao0", voltage=5, duration=0.1)
                if program_parameters.save == True:
                 program_parameters.is_sampling = True
                 program_parameters.liveplot = False
                 time.sleep(.05)
                 number_of_samples = program_parameters.number_samples
                 #motor_to_cycle_thread.start()
                
                 #sensor_data = data_collection(number_of_samples, frequency)

                 shared_sensor_data = []

                 data_thread = threading.Thread(target=lambda: shared_sensor_data.extend(data_collection(number_of_samples, frequency)))
                 data_thread.start()
                 print('moving to objective')
                 motor.move_to(target_position)
                 time.sleep(0.1)

                 while motor.is_in_motion:
                     #print('in first while')
                     time.sleep(.01)
                 print('moving back')

                #print(program_parameters.position_get)
                 output_constant_voltage_for_duration("Dev1/ao0", voltage=5, duration=0.1)
                 motor.move_to(initial_position)

                 while motor.is_in_motion:
                     #print('in second while')
                     time.sleep(.01)
                 
                 while program_parameters.is_sampling is True:
                  time.sleep(0.01)
                  #print('in third while')
                 output_constant_voltage_for_duration("Dev1/ao0", voltage=5, duration=0.1) 
                 time.sleep(0.5)
                
                 csv_output(shared_sensor_data, program_parameters.position_get)
                 program_parameters.liveplot = True #restarts while loop allowing live plots to function
                 thread = threading.Thread(target=update_data) #restarts thread application for live plots
                 thread.start() 



    
def move_forward():

    if program_parameters.move_forward==True:
        Accel_Get = dpg.get_value(accel)  #These 4 lines fetch the  our inputs from the GUI and assign them to varibles
        Velo_Get = dpg.get_value(velo)
        motor.set_velocity_parameters(0,Accel_Get,Velo_Get)
        motor.move_velocity(1)
    else:
        motor.stop_profiled()

def move_forward_button_state(sender):
    # print(program_parameters.move_forward)
    # print(program_parameters.move_forward)
    program_parameters.move_forward = not program_parameters.move_forward
    dpg.bind_item_theme(sender, item_theme_GREEN if program_parameters.move_forward is True else item_theme_RED)
    move_forward()

def move_backward():

    if program_parameters.move_backward==True:
        Accel_Get = dpg.get_value(accel)  #These 4 lines fetch the  our inputs from the GUI and assign them to varibles
        Velo_Get = dpg.get_value(velo)
        motor.set_velocity_parameters(0,Accel_Get,Velo_Get)
        motor.move_velocity(2)
    else:
        motor.stop_profiled()

def move_backward_button_state(sender):
    # print(program_parameters.move_forward)
    # print(program_parameters.move_forward)
    program_parameters.move_backward = not program_parameters.move_backward
    dpg.bind_item_theme(sender, item_theme_GREEN if program_parameters.move_backward is True else item_theme_RED)
    move_backward()
        

#GUI That references functions
# with dpg.item_handler_registry(tag="move_forward_true") as handler:
#     dpg.add_item_active_handler(callback=move_forward)

# dpg.bind_item_handler_registry("move_forward", "move_forward_true")


def set_constant_voltage(task, voltage):
    task.write(voltage, auto_start=True)

def output_constant_voltage_for_duration(channel, voltage, duration):
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan(channel)
        
        # Set the voltage
        set_constant_voltage(task, voltage)

        print(f"Constant voltage of {voltage} V is being outputted for {duration} seconds.")
        
        # Wait for the specified duration
        time.sleep(duration)

        # Stop the task (stop supplying voltage)
        set_constant_voltage(task, 0)
        task.stop()


with dpg.font_registry():
    default_font = dpg.add_font(r"C:\Users\lapto\Desktop\OpenSans-VariableFont_wdth,wght.ttf", 20)  # Set font size to 20
dpg.bind_font(default_font)


with dpg.theme() as item_theme_PINK: #creates item theme that colors buttons pink
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (235, 99, 144), category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0, category=dpg.mvThemeCat_Core)

with dpg.theme() as item_theme_RED: #creates item them that is red
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (226, 61, 0), category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0, category=dpg.mvThemeCat_Core)
        #dpg.add_theme_style(dpg.mvThemeCol_Text, (0, 0, 0), category=dpg.mvThemeCat_Core)

with dpg.theme() as item_theme_GREEN:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (61, 143, 56), category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0, category=dpg.mvThemeCat_Core)

with dpg.window(label="LST Settings", width=400, height=250, pos=(151,0)): #GUI with inputs for LTS
    Move_forward = dpg.add_button(label="move forward", tag="move_forward", callback=move_forward_button_state)
    Move_Backward = dpg.add_button(label="move backwards",tag="move_backward",callback=move_backward_button_state)

    Home = dpg.add_button(label="HOME STAGE")

    
    with dpg.popup(dpg.last_item(), mousebutton=dpg.mvMouseButton_Left, modal=True, tag="modal_id"):
        dpg.add_text("Do you want to home the stage? check if LVIT and stablizers are out of the way")
        YES_HOME = dpg.add_button(label="Yes, home the stage", callback=popup_funct_home)
        NO_HOME = dpg.add_button(label="Negative, do not home the stage", callback=lambda: dpg.configure_item("modal_id", show=False))


    accel = dpg.add_input_float(label="acceleration", default_value =1, tag = "Accel")
    velo = dpg.add_input_float(label="velocity", default_value =5, )
    position = dpg.add_input_float(label="move to (abs position)", default_value =5, )
    Location = dpg.add_input_float(label = "current position mm", default_value = MotorPos, tag = "location" )

with dpg.window(label="MYDAC", width=400, height=250, pos=(551,0)):
    samplerate = dpg.add_input_float(label="sample rate HZ", default_value =100, min_value=0)
    run_button = dpg.add_button(label="Execute", callback=execute_cycles)
    initial_position_input = dpg.add_input_float(label="Initial Position (mm)", default_value=0)
    target_position_input = dpg.add_input_float(label="Target Position (mm)", default_value=10)
    cycles_input = dpg.add_input_float(label="Number of cycles", default_value=1)
    cycles_count = dpg.add_input_float(label="current cycle", default_value=current_cycle)
    dpg.configure_item(cycles_count, readonly=True)
    


with dpg.window(width=150, height=250,pos=(1,0)):
    RUN = dpg.add_button(label = "RUN", width=100, height=100, callback=run_function)
    SAVE = dpg.add_button(label="SAVE", callback=button_callback, user_data=(True, item_theme_GREEN, item_theme_RED,), width= 100, height=100)
    # print(liveplot)

with dpg.window(label='LVIT', tag='lvit',width=800, height=600, pos=(00,250)):

    with dpg.plot(label='LVIT', height=-1, width=-1, tag="LVIT PLOT"):
        # optionally create legend
        dpg.add_plot_legend()
        
        # REQUIRED: create x and y axes, set to auto scale.
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label='x', tag='x_axis')
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='y', tag='y_axis')

        # series belong to a y axis. Note the tag name is used in the update
        # function update_data
        
        dpg.add_line_series(x=list(data_x),y=list(data_y), 
                            label='LVIT', parent='y_axis', 
                            tag='series_tag')

with dpg.window(label='inductor', tag='induc',width=800, height=600, pos=(810,250)):

    with dpg.plot(label='INDUCTOR', height=-1, width=-1):
        # optionally create legend
        dpg.add_plot_legend()

        # REQUIRED: create x and y axes, set to auto scale.
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label='x', tag='x_axis2')
        z_axis = dpg.add_plot_axis(dpg.mvYAxis, label='z', tag='z_axis')

        # series belong to a y axis. Note the tag name is used in the update
        # function update_data
        dpg.add_line_series(x=list(data_x),y=list(data_z), 
                            label='INDUCTOR', parent='z_axis', 
                            tag='series_tag2')



dpg.bind_item_theme(RUN, item_theme_PINK)
dpg.bind_item_theme(Home, item_theme_RED)
dpg.bind_item_theme(NO_HOME, item_theme_RED)
dpg.bind_item_theme(YES_HOME, item_theme_GREEN)


dpg.create_viewport(title='Cantilever Interface', width=1800, height=1200)
dpg.setup_dearpygui()
dpg.show_viewport()
liveplotthread = threading.Thread(target=update_data)
positionupdatethread = threading.Thread(target=positionupdate)
liveplotthread.start()
positionupdatethread.start()

dpg.start_dearpygui()


dpg.destroy_context()


apt.our_cleanup()

