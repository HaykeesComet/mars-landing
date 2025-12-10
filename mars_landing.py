"""
================================================================================
MARS LANDING FUEL MANAGEMENT SYSTEM
================================================================================
Real-time fuel monitoring, prediction, and alert system for Mars powered descent
"""

import time
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# CONSTANTS
# ============================================================================
GRAVITY_MARS = 3.71  # m/s²
SAFE_RESERVE = 100  # kg minimum reserve fuel
BURN_RATE_TOLERANCE = 0.15  # 15% deviation triggers anomaly flag
ALERT_THRESHOLD = 30  # seconds before critical event to alert
UPDATE_FREQUENCY = 0.5  # seconds between calculations


# ============================================================================
# DATA STRUCTURES
# ============================================================================
@dataclass
class MissionPhase:
    """Represents a mission phase with its characteristics"""
    name: str
    nominal_burn_rate: float  # kg/s
    duration: float  # seconds
    gravity_loss_factor: float = 0.0  # fraction of additional fuel needed


@dataclass
class ConsumptionData:
    """Output from burn rate calculation"""
    actual_burn_rate: float
    deviation_percent: float
    anomaly_flag: bool
    current_fuel: float


@dataclass
class FuelPrediction:
    """Output from fuel requirement prediction"""
    required_fuel: float
    with_margin: float
    breakdown: List[Dict[str, Any]]
    confidence: float


@dataclass
class SafetyEvaluation:
    """Output from safety margin evaluation"""
    status: str  # NOMINAL, CAUTION, CRITICAL
    fuel_margin: float
    abort_capable: bool
    time_remaining: float
    fuel_sufficient: bool


@dataclass
class AlertPackage:
    """Output from alert generation"""
    warnings: List[str]
    recommendations: List[str]
    priority: str


# ============================================================================
# MISSION CONFIGURATION
# ============================================================================
PHASE_BURN_RATES = {
    "powered_descent": 8.0,
    "constant_deceleration": 6.0,
    "final_approach": 4.0,
    "landing": 12.0
}

REMAINING_MANEUVERS = {
    "powered_descent": [
        MissionPhase("constant_deceleration", 6.0, 40, 0.08),
        MissionPhase("final_approach", 4.0, 20, 0.05),
        MissionPhase("landing", 12.0, 10, 0.03)
    ],
    "constant_deceleration": [
        MissionPhase("final_approach", 4.0, 20, 0.05),
        MissionPhase("landing", 12.0, 10, 0.03)
    ],
    "final_approach": [
        MissionPhase("landing", 12.0, 10, 0.03)
    ],
    "landing": []
}


# ============================================================================
# FUEL MANAGEMENT SYSTEM CLASS
# ============================================================================
class MarsLandingFuelSystem:
    """Main fuel management system for Mars landing operations"""
    
    def __init__(self, initial_fuel: float, mission_phase: str = "powered_descent"):
        """
        Initialize the fuel management system
        
        Args:
            initial_fuel: Starting fuel mass in kg
            mission_phase: Current mission phase identifier
        """
        self.previous_fuel_mass = initial_fuel
        self.previous_timestamp = time.time()
        self.mission_phase = mission_phase
        self.alert_history = []
        
        # Simulated sensor data (would be real sensors in production)
        self.current_fuel_mass = initial_fuel
        self.altitude = 5000.0  # meters
        self.velocity = 80.0  # m/s
        
    # ========================================================================
    # SUBPROBLEM 1: Calculate Real-Time Fuel Consumption Rate
    # ========================================================================
    def calculate_burn_rate(self, current_fuel: float, current_time: float) -> ConsumptionData:
        """
        Calculate actual fuel burn rate and detect anomalies
        
        Args:
            current_fuel: Current fuel mass from sensor (kg)
            current_time: Current timestamp (seconds)
            
        Returns:
            ConsumptionData with burn rate, deviation, anomaly flag, and current fuel
        """
        # Calculate time delta
        time_delta = current_time - self.previous_timestamp
        
        if time_delta <= 0:
            time_delta = 0.001  # Prevent division by zero
        
        # Calculate actual consumption
        fuel_consumed = self.previous_fuel_mass - current_fuel
        actual_burn_rate = fuel_consumed / time_delta
        
        # Get expected rate for current phase
        nominal_burn_rate = PHASE_BURN_RATES.get(self.mission_phase, 6.0)
        
        # Detect anomalies
        if nominal_burn_rate > 0:
            deviation = (actual_burn_rate - nominal_burn_rate) / nominal_burn_rate
        else:
            deviation = 0.0
            
        anomaly_detected = abs(deviation) > BURN_RATE_TOLERANCE
        
        # Update stored values
        self.previous_fuel_mass = current_fuel
        self.previous_timestamp = current_time
        
        return ConsumptionData(
            actual_burn_rate=actual_burn_rate,
            deviation_percent=deviation * 100,
            anomaly_flag=anomaly_detected,
            current_fuel=current_fuel
        )
    
    # ========================================================================
    # SUBPROBLEM 2: Predict Fuel Requirements for Remaining Mission
    # ========================================================================
    def predict_fuel_requirements(self, burn_rate: float, anomaly_detected: bool) -> FuelPrediction:
        """
        Predict total fuel needed for remaining mission phases
        
        Args:
            burn_rate: Current actual burn rate (kg/s)
            anomaly_detected: Whether consumption anomaly is present
            
        Returns:
            FuelPrediction with required fuel, margins, breakdown, and confidence
        """
        # Retrieve planned maneuvers for remaining mission
        remaining_maneuvers = REMAINING_MANEUVERS.get(self.mission_phase, [])
        
        total_required_fuel = 0.0
        fuel_breakdown = []
        
        # Calculate fuel for each remaining phase
        for maneuver in remaining_maneuvers:
            # Adjust for actual burn rate vs. planned
            if maneuver.nominal_burn_rate > 0:
                burn_adjustment = burn_rate / maneuver.nominal_burn_rate
            else:
                burn_adjustment = 1.0
            
            # Calculate fuel needed
            phase_fuel = maneuver.duration * burn_rate * burn_adjustment
            
            # Add gravity losses and inefficiencies
            adjusted_fuel = phase_fuel * (1 + maneuver.gravity_loss_factor)
            
            total_required_fuel += adjusted_fuel
            
            fuel_breakdown.append({
                "phase": maneuver.name,
                "fuel_required": adjusted_fuel,
                "duration": maneuver.duration
            })
        
        # Add uncertainty margin based on current anomalies
        if anomaly_detected:
            uncertainty_margin = total_required_fuel * 0.20  # 20% buffer
        else:
            uncertainty_margin = total_required_fuel * 0.05  # 5% buffer
        
        total_with_margin = total_required_fuel + uncertainty_margin
        
        if total_required_fuel > 0:
            confidence_level = (1 - uncertainty_margin / total_required_fuel) * 100
        else:
            confidence_level = 100.0
        
        return FuelPrediction(
            required_fuel=total_required_fuel,
            with_margin=total_with_margin,
            breakdown=fuel_breakdown,
            confidence=confidence_level
        )
    
    # ========================================================================
    # SUBPROBLEM 3: Evaluate Safety Margins and Abort Capability
    # ========================================================================
    def evaluate_safety_margins(self, current_fuel: float, required_fuel: float, 
                                burn_rate: float) -> SafetyEvaluation:
        """
        Determine mission status and abort capability
        
        Args:
            current_fuel: Current available fuel (kg)
            required_fuel: Predicted fuel requirement (kg)
            burn_rate: Current burn rate (kg/s)
            
        Returns:
            SafetyEvaluation with status, margins, abort capability, and time remaining
        """
        # Calculate fuel margin
        fuel_margin = current_fuel - required_fuel - SAFE_RESERVE
        
        # Check if abort is possible
        abort_maneuver_fuel = self._calculate_abort_to_orbit_fuel()
        abort_capable = (current_fuel >= abort_maneuver_fuel + 50)
        
        # Determine mission status
        if fuel_margin >= 0 and abort_capable:
            status = "NOMINAL"
        elif fuel_margin >= -50 or abort_capable:
            status = "CAUTION"
        else:
            status = "CRITICAL"
        
        # Calculate time to depletion
        if burn_rate > 0:
            time_to_depletion = current_fuel / burn_rate
        else:
            time_to_depletion = float('inf')
        
        return SafetyEvaluation(
            status=status,
            fuel_margin=fuel_margin,
            abort_capable=abort_capable,
            time_remaining=time_to_depletion,
            fuel_sufficient=(fuel_margin >= 0)
        )
    
    def _calculate_abort_to_orbit_fuel(self) -> float:
        """
        Calculate fuel required for abort-to-orbit maneuver
        
        Returns:
            Required fuel in kg
        """
        # Simplified calculation based on altitude and velocity
        # In real system, this would use full trajectory analysis
        altitude_factor = max(0, self.altitude / 5000.0)
        velocity_factor = self.velocity / 100.0
        
        base_abort_fuel = 200  # kg base requirement
        altitude_penalty = 50 * (1 - altitude_factor)
        velocity_penalty = 30 * velocity_factor
        
        return base_abort_fuel + altitude_penalty + velocity_penalty
    
    # ========================================================================
    # SUBPROBLEM 4: Generate Alerts and Recommendations
    # ========================================================================
    def generate_alerts(self, safety_eval: SafetyEvaluation, 
                       consumption_data: ConsumptionData,
                       prediction: FuelPrediction) -> AlertPackage:
        """
        Generate prioritized warnings and actionable recommendations
        
        Args:
            safety_eval: Safety evaluation results
            consumption_data: Fuel consumption data
            prediction: Fuel requirement predictions
            
        Returns:
            AlertPackage with warnings, recommendations, and priority
        """
        warnings = []
        recommendations = []
        
        # Critical fuel shortage
        if not safety_eval.fuel_sufficient:
            warnings.append("CRITICAL: Insufficient fuel for nominal landing")
            fuel_deficit = abs(safety_eval.fuel_margin)
            warnings.append(f"DEFICIT: {fuel_deficit:.1f} kg shortfall")
            
            if safety_eval.abort_capable:
                recommendations.append("IMMEDIATE: Consider abort to orbit")
            else:
                recommendations.append("EMERGENCY: Optimize trajectory NOW")
                recommendations.append("Consider emergency landing procedures")
        
        # Abort capability lost
        if not safety_eval.abort_capable and safety_eval.status != "CRITICAL":
            warnings.append("WARNING: Abort-to-orbit window closing")
        
        # Anomalous consumption
        if consumption_data.anomaly_flag:
            deviation = consumption_data.deviation_percent
            warnings.append(f"ALERT: Burn rate {deviation:+.1f}% from nominal")
            recommendations.append("Investigate thruster performance")
        
        # Time-critical alert
        if safety_eval.time_remaining < ALERT_THRESHOLD:
            warnings.append(f"TIME CRITICAL: {safety_eval.time_remaining:.1f}s to depletion")
        
        # Positive status with margin
        if safety_eval.status == "NOMINAL" and len(warnings) == 0:
            recommendations.append("Continue nominal descent profile")
        
        return AlertPackage(
            warnings=warnings,
            recommendations=recommendations,
            priority=safety_eval.status
        )
    
    # ========================================================================
    # MAIN MONITORING CYCLE
    # ========================================================================
    def monitor_cycle(self) -> Dict[str, Any]:
        """
        Execute complete monitoring cycle through all subproblems
        
        Returns:
            Dictionary with complete system status
        """
        current_time = time.time()
        
        # Step 1: Calculate consumption (Subproblem 1)
        consumption_data = self.calculate_burn_rate(
            self.current_fuel_mass, 
            current_time
        )
        
        # Step 2: Predict requirements (Subproblem 2)
        fuel_prediction = self.predict_fuel_requirements(
            consumption_data.actual_burn_rate,
            consumption_data.anomaly_flag
        )
        
        # Step 3: Evaluate safety (Subproblem 3)
        safety_status = self.evaluate_safety_margins(
            consumption_data.current_fuel,
            fuel_prediction.with_margin,
            consumption_data.actual_burn_rate
        )
        
        # Step 4: Generate alerts (Subproblem 4)
        alerts = self.generate_alerts(
            safety_status,
            consumption_data,
            fuel_prediction
        )
        
        # Calculate fuel at touchdown
        fuel_at_touchdown = consumption_data.current_fuel - fuel_prediction.required_fuel
        
        # Compile complete status
        status = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "mission_phase": self.mission_phase,
            "status": safety_status.status,
            "current_fuel": consumption_data.current_fuel,
            "burn_rate": consumption_data.actual_burn_rate,
            "burn_rate_deviation": consumption_data.deviation_percent,
            "anomaly_detected": consumption_data.anomaly_flag,
            "required_fuel": fuel_prediction.required_fuel,
            "fuel_margin": safety_status.fuel_margin,
            "fuel_at_touchdown": fuel_at_touchdown,
            "time_remaining": safety_status.time_remaining,
            "abort_capable": safety_status.abort_capable,
            "confidence": fuel_prediction.confidence,
            "warnings": alerts.warnings,
            "recommendations": alerts.recommendations,
            "altitude": self.altitude,
            "velocity": self.velocity
        }
        
        return status
    
    # ========================================================================
    # SIMULATION METHODS
    # ========================================================================
    def update_sensors(self, fuel_delta: float, altitude_delta: float = -50, 
                      velocity_delta: float = -2):
        """
        Simulate sensor updates (for testing/demonstration)
        
        Args:
            fuel_delta: Change in fuel mass (kg)
            altitude_delta: Change in altitude (m)
            velocity_delta: Change in velocity (m/s)
        """
        self.current_fuel_mass += fuel_delta
        self.altitude += altitude_delta
        self.velocity += velocity_delta
        
        # Ensure non-negative values
        self.current_fuel_mass = max(0, self.current_fuel_mass)
        self.altitude = max(0, self.altitude)
        self.velocity = max(0, self.velocity)
    
    def set_mission_phase(self, phase: str):
        """Set the current mission phase"""
        if phase in PHASE_BURN_RATES:
            self.mission_phase = phase


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================
def display_status(status: Dict[str, Any]):
    """Display formatted system status"""
    print("\n" + "="*80)
    print(f"MARS LANDING FUEL MANAGEMENT SYSTEM - {status['timestamp']}")
    print("="*80)
    print(f"\nMISSION PHASE: {status['mission_phase'].upper()}")
    print(f"SYSTEM STATUS: {status['status']}")
    print(f"\n{'FUEL STATE':-^80}")
    print(f"  Current Fuel:        {status['current_fuel']:.1f} kg")
    print(f"  Burn Rate:           {status['burn_rate']:.2f} kg/s ({status['burn_rate_deviation']:+.1f}%)")
    print(f"  Required Fuel:       {status['required_fuel']:.1f} kg")
    print(f"  Fuel Margin:         {status['fuel_margin']:+.1f} kg")
    print(f"  Est. at Touchdown:   {status['fuel_at_touchdown']:.1f} kg")
    
    print(f"\n{'SAFETY METRICS':-^80}")
    print(f"  Time to Depletion:   {status['time_remaining']:.1f} s")
    print(f"  Abort Capable:       {'YES' if status['abort_capable'] else 'NO'}")
    print(f"  Prediction Conf:     {status['confidence']:.1f}%")
    print(f"  Anomaly Detected:    {'YES' if status['anomaly_detected'] else 'NO'}")
    
    print(f"\n{'TRAJECTORY':-^80}")
    print(f"  Altitude:            {status['altitude']:.1f} m")
    print(f"  Velocity:            {status['velocity']:.1f} m/s")
    
    if status['warnings']:
        print(f"\n{'WARNINGS':-^80}")
        for warning in status['warnings']:
            print(f"  ⚠ {warning}")
    
    if status['recommendations']:
        print(f"\n{'RECOMMENDATIONS':-^80}")
        for rec in status['recommendations']:
            print(f"  → {rec}")
    
    print("\n" + "="*80 + "\n")


# ============================================================================
# TEST SCENARIOS
# ============================================================================
def run_example_1_nominal():
    """Example 1: Nominal Operations (Mid-Descent)"""
    print("\n" + "#"*80)
    print("# EXAMPLE 1: NOMINAL OPERATIONS (MID-DESCENT)")
    print("#"*80)
    
    system = MarsLandingFuelSystem(initial_fuel=853, mission_phase="constant_deceleration")
    system.altitude = 2000
    system.velocity = 45
    
    # Simulate 0.5 second passage with nominal burn
    time.sleep(0.5)
    system.update_sensors(fuel_delta=-3.0, altitude_delta=0, velocity_delta=0)
    
    status = system.monitor_cycle()
    display_status(status)


def run_example_2_anomalous():
    """Example 2: Anomalous Consumption (Thruster Leak)"""
    print("\n" + "#"*80)
    print("# EXAMPLE 2: ANOMALOUS CONSUMPTION (THRUSTER LEAK)")
    print("#"*80)
    
    system = MarsLandingFuelSystem(initial_fuel=627, mission_phase="constant_deceleration")
    system.altitude = 1200
    system.velocity = 38
    
    # Simulate 0.5 second passage with high burn rate
    time.sleep(0.5)
    system.update_sensors(fuel_delta=-7.0, altitude_delta=0, velocity_delta=0)
    
    status = system.monitor_cycle()
    display_status(status)


def run_example_3_critical():
    """Example 3: Critical Fuel Shortage (Too Late to Abort)"""
    print("\n" + "#"*80)
    print("# EXAMPLE 3: CRITICAL FUEL SHORTAGE (TOO LATE TO ABORT)")
    print("#"*80)
    
    system = MarsLandingFuelSystem(initial_fuel=178, mission_phase="final_approach")
    system.altitude = 450
    system.velocity = 12
    
    # Simulate 0.5 second passage
    time.sleep(0.5)
    system.update_sensors(fuel_delta=-3.0, altitude_delta=0, velocity_delta=0)
    
    status = system.monitor_cycle()
    display_status(status)


def run_example_4_emergency():
    """Example 4: Fuel Depletion Imminent (Emergency)"""
    print("\n" + "#"*80)
    print("# EXAMPLE 4: FUEL DEPLETION IMMINENT (EMERGENCY)")
    print("#"*80)
    
    system = MarsLandingFuelSystem(initial_fuel=118, mission_phase="landing")
    system.altitude = 95
    system.velocity = 3
    
    # Simulate 0.5 second passage with high landing burn
    time.sleep(0.5)
    system.update_sensors(fuel_delta=-6.0, altitude_delta=0, velocity_delta=0)
    
    status = system.monitor_cycle()
    display_status(status)


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("MARS LANDING FUEL MANAGEMENT SYSTEM - TEST SUITE")
    print("="*80)
    
    # Run all example test cases
    run_example_1_nominal()
    run_example_2_anomalous()
    run_example_3_critical()
    run_example_4_emergency()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80 + "\n")
