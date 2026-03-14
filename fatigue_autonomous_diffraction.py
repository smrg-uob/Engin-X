#Wan Wan Mohammad
#Joe Kelleher
#Simon McKendrey

# 12 March 2026 

# LCF where the neutron diffraction measurements are conducted at defined cycles including Bauschinger Effect
from time import sleep

import numpy as np
from genie_python.genie_startup import *
import genie_python
import threading


# %%General Test parameters
name = "SampleID"  # sample/test name
NumCycles = 151  # total number of cycles to be conducted but will fail once drop 50% in max stress (hard limit)
d0_Stress = 0  # in MPa. The stress used for d0 measurement
StrainAmp = 0.3  # in %, strain amplitude
StrainRate = 0.1  # in %/s Plan B Plan A=0.1%, Plan C=0.3%
MeasureTime = 7  # in uAh 
StressDropThreshold = 0.5  # 50% drop in maximum stress is considered to be sample failure
YM1 = 118300  # MPa Youngs modulus AsDrawn
YM2 = 85000  # MPa Youngs modulus Solution Annealed
YM = YM1  # Please change for sample 2


# Residual Strain Measurement test parameters
Cycles = [] # Create list of cycle numbers in which neutron measurements are to be made. Other cycles are loading without measurement
Cycles.extend(range(1, 6, 1))  # Every cycle up to 5
Cycles.extend([10,30,50,70,80,100,150])  # Every 10 cycles up to 100
#Cycles.extend(range(200, 1001, 100))  # Every 100 cycles up to 1000
#Cycles.extend(range(1200, 2001, 200))  # Every 200 cycles up to 2000
#Cycles.extend(range(2500, 100001, 500))  # Every 500 cycles until failure

# Flags to be set when maximum load in each cycle falls below XX% or highest value in first cycle
Flag90 = False
Flag80 = False
Flag70 = False
Flag60 = False

##############################################################################
# %%----Functions-------------

def RampTime(Start, End, Rate):
    """Calculate time for a ramp operation at Rate going from Start to End"""
    return (abs(End - Start)) / Rate  # seconds

def StrainRamp(TargetStrain, StrainRate):
    """Ramp in strain control from the current strain to a specified target strain value, at StrainRate"""
    CurStrain = g.cget("strain")["value"]
    Time = RampTime(CurStrain, TargetStrain, StrainRate)
    Time = max(Time, 0.1)
    inst.stress_rig._set_stressrig_value(Time, "strain_step_time")
    inst.stress_rig._update_control_channel("strain")
    inst.stress_rig._set_stressrig_setpoint(TargetStrain, Time, "strain")
    return

def StressRamp(TargetStress):
    CurStress = g.cget("stress")["value"]
    # FIX: time should depend on delta stress, and convert StrainRate (%/s) -> strain/s
    epsdot = StrainRate / 100.0
    d_sigma = abs(TargetStress - CurStress)
    Time = d_sigma / (YM * max(epsdot, 1e-12))
    Time = max(Time, 0.1)
    inst.stress_rig._set_stressrig_value(Time, "strain_step_time")
    inst.stress_rig._update_control_channel("stress")
    inst.stress_rig._set_stressrig_setpoint(TargetStress, Time, "stress")
    return

def check_failure(max_recorded_stress):
    CurStress = g.cget("stress")["value"]
    return CurStress <= (StressDropThreshold * max_recorded_stress)

# (placeholders): pause/resume Instron cyclic waveform Check with Joe ----
def PauseCyclicWaveform():
    """
    PLACEHOLDER: replace with the Engin-X/Instron command that pauses/stops the running waveform.
    """
    # e.g. inst.stress_rig.pause()  (example only)
    # e.g. inst.stress_rig._stop_program()
    g.cset("wave_stop", 1) # Finish the current waveform. wave_stop block should point to TE:ENGINX67:INSTRONA_01:WAVE:STOP:SP
    g.waitfor(block="wave_running", value="Not running") # Allow cycle to finish
    g.cset("stress_ramp_wftyp", "Absolute ramp") # Go back to absolute mode on all channels
    g.cset("strain_ramp_wftyp", "Absolute ramp") # Strain waveform type does not update in block display, even though PV is set correct???
    g.cset("pos_ramp_wftyp", "Absolute ramp")
    return

def ResumeCyclicWaveform():
    """
    PLACEHOLDER: replace with the Engin-X/Instron command that resumes/starts the waveform.
    """
    # e.g. inst.stress_rig.resume() (example only)
    # e.g. inst.stress_rig._start_program()
    inst.stress_rig._update_control_channel("strain") # changes the instron control mode to strain
    g.cset("frequency", 0.08333)
    sleep(1)  
    g.cset("frequency", 0.08333)
    g.cset("wave_start", 1) # starts the cyclic waveform setup in the GUI
    return

# NEW (optional): read real cycle count from rig if available ----
#def get_cycle_count():
#    """
#    Preferred: use a real cycle counter from the rig.
#    If g.cget("cycle") does not exist on enginx system, Joe can advise?
#    """
#    return g.cget("cycle")["value"]  # <-- change key name if needed

class CycleWatcher:
    def __init__(self, LowThreshold, HighThreshold, Channel):
        self.CurrentCycle = 0
        self.CurrentState = "Intermediate"
        self.StatesThisCycle = ["TestStart"]
        self.HighThreshold = HighThreshold
        self.LowThreshold = LowThreshold
        self.LatestHighPeak = HighThreshold
        self.LatestLowPeak = LowThreshold
        self.PreviousCyclePeak = HighThreshold
        self.ClearMonitorFn = genie_python.genie_cachannel_wrapper.CaChannelWrapper.add_monitor(name=Channel, call_back_function=self.NewValue)
        genie_python.genie_cachannel_wrapper.CaChannelWrapper.poll()  # Needed to flush commands like this to IOC
        self.lock = threading.Lock()
    def NextCycle(self):
        return self.CurrentCycle + 1
    def NewValue(self, Value, AlarmSeverity=None, AlarmStatus=None):
        """Function to be called (somehow...) whenever rig value changes. Alarm parameters for compatibility with 
           CaChannelWrapper.add_monitor as a way to monitor rig value changes"""
        with self.lock:
            if Value > self.HighThreshold and self.CurrentState != "High":
                self.CurrentState = "High"
            elif (self.HighThreshold >= Value >= self.LowThreshold) and (self.CurrentState != "Intermediate"):
                self.CurrentState = "Intermediate"
            elif Value < self.LowThreshold and self.CurrentState != "Low":
                self.CurrentState = "Low"
            if self.StatesThisCycle[-1] != self.CurrentState:
                self.StatesThisCycle.append(self.CurrentState)
            # Look at recent states to decide if we have just completed a cycle
            if (self.CurrentState == "High") and (("Low" in self.StatesThisCycle) or ("TestStart" in self.StatesThisCycle)):
                # We are "High", having been "Low" since last cycle increment
                self.StatesThisCycle = ["CycleStart"]
                self.StatesThisCycle.append(self.CurrentState)
                self.CurrentCycle = self.CurrentCycle + 1
                self.PreviousCyclePeak = self.LatestHighPeak # Record this value for rest of script to query
                self.LatestHighPeak = self.HighThreshold
                self.LatestLowPeak = self.LowThreshold
            # Update peak values
            if self.CurrentState == "High" and Value > self.LatestHighPeak:
                self.LatestHighPeak = Value
            if self.CurrentState == "Low" and Value < self.LatestLowPeak:
                self.LatestLowPeak = Value

def MakeNeutronMeasurement(CycleCount):
    """Make a neutron diffraction measurement at current point in load cycle. Rig values and the supplied CycleCount used for run title"""
    CurrentStrainValue = g.cget("strain")["value"]
    CurrentStressValue = g.cget("stress")["value"]
    CurrentPositionValue = g.cget("position")["value"]
    g.begin()
    g.change_title(
        f"{name};{CurrentStrainValue:1.1f}%;{CurrentStressValue:1.1f}MPa;{CurrentPositionValue:1.1f}mm;Cycle{CycleCount:1f}")
    
    #sleep(1) dry run 
     g.waitfor(uamps=MeasureTime)
    g.end()

def CycleWithNeutrons(CycleCount):
    # Ensure waveform is paused before stepping points, though will typically already be paused (?)
    PauseCyclicWaveform()

    # Point 2: Stress-free after tension
    StressRamp(d0_Stress)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 2")
    # Point 3: 0% Strain before compression
    StrainRamp(0.0, StrainRate)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 3")
    # Point 4: Min strain
    StrainRamp(-StrainAmp, StrainRate)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 4")
    # Point 5: Stress-free after compression
    StressRamp(d0_Stress)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 5")
    # Point 6: 0% strain before tension
    StrainRamp(0.0, StrainRate)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 6")
    # Point 7: back to +max strain
    StrainRamp(StrainAmp, StrainRate)
    MakeNeutronMeasurement(CycleCount)
    print("Stopped to 'measure' point 7")
    
    # Don't restart cycling yet as next cycle could also be a neutron measurement



##############################################################################
# %%Conduct the experiment
# IMPORTANT CHANGE: do NOT generate cycles by StrainRamp in Python.
# Instead, rely on Instron waveform running continuously.# Need to check with Joe

# Set up background watcher of cycle count and peak stress values in cycle
ThisCyclicTest = CycleWatcher(-30, 30, "TE:ENGINX67:INSTRONA_01:STRESS")                  # Can use/change STRESS:STEP:TIME for testing without actual loading

# %%Start the test and record the max stress
##StrainRamp(StrainAmp, StrainRate)  # go to initial peak strain
#E0: 0%
StrainRamp(0.0,StrainRate)
g.begin()
g.change_title("{};E0;0%".format(name))
print("Stopped to 'measure' 0.00")
#sleep(1)
g.waitfor(uamps=MeasureTime)
g.end()

#E1:0.05%
StrainRamp(0.05,StrainRate)
g.begin()
g.change_title("{};E0;0.05%".format(name))
print("Stopped to 'measure' 0.05")
#sleep(1)
g.waitfor(uamps=MeasureTime)
g.end()

#E2: 0.10%
StrainRamp(0.10,StrainRate)
g.begin()
g.change_title("{};E0;0.10%".format(name))
print("Stopped to 'measure' 0.10")
#sleep(1)
g.waitfor(uamps=MeasureTime)
g.end()

#E3: 0.15%
StrainRamp(0.15,StrainRate)
g.begin()
g.change_title("{};E0;0.15%".format(name))
print("Stopped to 'measure' 0.15")
#sleep(1)
g.waitfor(uamps=MeasureTime)
g.end()

#E4:0.22%
StrainRamp(0.22,StrainRate)
g.begin()
g.change_title("{};E0;0.22%".format(name))
print("Stopped to 'measure'0.22")
#sleep(1)
g.waitfor(uamps=MeasureTime)
g.end()

StrainRamp(StrainAmp, StrainRate)  # go to initial peak strain
max_recorded_stress = ThisCyclicTest.LatestHighPeak #   g.cget("stress")["value"]

# Measure at Point 1 (Max Strain +0.3%) before cycling starts
MakeNeutronMeasurement(0)
print("Stopped to 'measure' point 1")

# Use real rig cycle count if available
LastCompletedCycle = 0

# ThisCyclicTest.CycleCount increments on transition from Intermediate to High, 
# e.g. towards end of previous cycle in time for a Stop command to avoid going to next cycle
while  ThisCyclicTest.CurrentCycle < NumCycles:
    # Check if current cycle (or next cycle after a cycle about to finish, see above) is new, sleep and loop if not
    CurrentCycle = int(ThisCyclicTest.CurrentCycle)
    if CurrentCycle == LastCompletedCycle:
        # nothing new yet; reduce CPU load / polling rate
        sleep(0.01)
        continue
    
    print(f"About to start cycle {CurrentCycle}")
    ##last_cycle = cycle

    # Failure check
    #if ThisCyclicTest.LatestHighPeak <= (StressDropThreshold * max_recorded_stress):
    #    print("Test stopped at cycle {} due to 50% drop in maximum stress.")
    #    break

    # Measurement logic
    if CurrentCycle in Cycles:
        CycleWithNeutrons(CurrentCycle)

    elif ThisCyclicTest.PreviousCyclePeak <= 0.9 * max_recorded_stress and Flag90 == False:
        CycleWithNeutrons(CurrentCycle)
        Flag90 = True

    elif ThisCyclicTest.PreviousCyclePeak <= 0.8 * max_recorded_stress and Flag80 == False:
        CycleWithNeutrons(CurrentCycle)
        Flag80 = True

    elif ThisCyclicTest.PreviousCyclePeak <= 0.7 * max_recorded_stress and Flag70 == False:
        CycleWithNeutrons(CurrentCycle)
        Flag70 = True

    elif ThisCyclicTest.PreviousCyclePeak <= 0.6 * max_recorded_stress and Flag60 == False:
        CycleWithNeutrons(CurrentCycle)
        Flag60 = True
    else:
        ResumeCyclicWaveform()
        while ThisCyclicTest.CurrentState != "Low":
            # Wait until this cycle is well underway before resuming checks of cycle count
            sleep(1)
        
    LastCompletedCycle = CurrentCycle # Cycle number CurrentCycle will already have completed by this point, or at least be running from ResumeCyclicWaveform() call

    # Update max recorded stress
    max_recorded_stress = max(max_recorded_stress, ThisCyclicTest.PreviousCyclePeak)



