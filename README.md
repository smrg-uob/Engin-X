##### **ENGIN-X Autonomous LCF Script (IBEX / Instron MiniTower)**



##### Overview

This repository contains a Python control script for performing in-situ fatigue (LCF) experiments on ENGIN-X using the Instron MiniTower stress rig and IBEX/Genie scripting.
The script is designed for autonomous cyclic loading with periodic neutron diffraction measurements.



##### System Architecture

The ENGIN-X Instron MiniTower is controlled through the IBEX control system.

###### 

###### Control chain:

Python Script (Genie / IBEX)
|
▼
IBEX IOC (ENGIN-X)
│
▼
Instron Console software
│
▼
Instron MiniTower controller
│
▼
Mechanical stress rig



Important notes:
The Instron rig is connected to a dedicated control PC (enginx-stress-1).
The Instron Console software must be running for IBEX control to function.





##### Experimental Workflow



###### The script performs the following sequence:



1. Initial Elastic Loading Measurements

Before cyclic loading begins, the script performs measurements at a small strain



2\. Start Cyclic Loading

After the elastic measurements:

&#x09;The Instron waveform generator begins continuous strain-controlled cycling

&#x09;The script monitors the cycle number using rig feedback



3\. Autonomous Cycle Monitoring

&#x09;The script continuously monitors:

&#x09;	current cycle number

&#x09;	peak tensile stress

&#x09;	peak compressive stress

4\. Neutron Diffraction Measurements

At predefined cycles the waveform is paused and diffraction measurements are taken.



5\. Failure Detection

The script monitors maximum stress during cycling.





##### Running the Script on ENGIN-X

Scripts are executed within the IBEX Genie Python environment.

Example command:

execfile(r"C:\\Scripts\\Wan\\Wan-PlanA-Autonomous\_New\_2.py")



###### Before running the script:



Ensure the Instron Console software is running.
Confirm the rig is in computer control.
Verify strain and load channels are calibrated.
Ensure no other computer is communicating with the stress rig.
Confirm waveform amplitude and strain limits are safe for the specimen.



##### **Authors**

Developed as part of PhD research on crystal plasticity validation and fatigue behaviour of OFHC copper for fusion applications.



University of Bristol
ENGIN-X Beamline Collaboration (ISIS Neutron and Muon Source)





##### **Disclaimer**

These scripts are provided for research purposes and may require

adaptation for different experimental configurations on ENGIN-X.

Always verify safety and machine parameters before running on

instrument control systems.

