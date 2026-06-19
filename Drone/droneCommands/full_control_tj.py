"""
================================================================================
 IOTROCOP KTV - THROTTLE + JOYSTICK CONTROL v2 (SITL VERSION - same code)
================================================================================
 MAPPING:
   - Throttle  (power_y)  -> Climb/Descend (smooth slew)
   - JOY X     (drone_x)  -> YAW   (right=CW, left=CCW)
   - JOY Y     (drone_y)  -> PITCH (up=forward, down=back)
   - ROLL                 -> DISABLED (always 0)
   - spin_y               -> DISABLED
================================================================================
"""

import asyncio
import socket
import struct
import time
from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityBodyYawspeed

UDP_IP = "0.0.0.0"
UDP_PORT = 5656
STATUS_IP = "192.168.100.1"
STATUS_PORT = 5659

THROTTLE_CENTER  = 2000
THROTTLE_DEADBAND = 150
JOY_X_CENTER     = 2000
JOY_X_DEADBAND   = 300
JOY_Y_CENTER     = 2000
JOY_Y_DEADBAND   = 300

MAX_VZ_UP    = 0.40
MAX_VZ_DOWN  = 0.20
MAX_VXY      = 3.00
MAX_YAW_RATE = 25.0

SLEW_VZ  = 0.015
SLEW_VXY = 0.080
SLEW_YAW = 2.0

SPIN_Y_CENTER   = 2189
SPIN_Y_DEADBAND = 400

MIN_GPS_SATS = 10
SETPOINT_HZ = 50
LOG_INTERVAL = 0.3
GROUND_DISARM_TIME = 2.0
AUTO_TAKEOFF_ALT = 0.5

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)
status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_status(mode, msg):
    try:
        status_sock.sendto(f"{mode}|{msg}".encode(), (STATUS_IP, STATUS_PORT))
    except Exception:
        pass

def parse_packet(data):
    if len(data) < 19:
        return None
    try:
        u = struct.unpack('<BhhhhhhBBHBB', data)
        if u[0] != 0xAA or u[-1] != 0x55:
            return None
        return {
            'drone_x': u[1], 'drone_y': u[2],
            'power_y': u[3], 'spin_y': u[4],
            'switch_states': u[9],
        }
    except Exception:
        return None

def apply_deadband(value, center, deadband):
    delta = value - center
    if abs(delta) < deadband:
        return 0.0
    return (delta - deadband) if delta > 0 else (delta + deadband)

def throttle_to_vz_target(power_y):
    offset = apply_deadband(power_y, THROTTLE_CENTER, THROTTLE_DEADBAND)
    if offset == 0:
        return 0.0
    if offset > 0:
        max_off = (4000 - THROTTLE_CENTER) - THROTTLE_DEADBAND
        return -min(offset / max_off, 1.0) * MAX_VZ_UP
    else:
        max_off = THROTTLE_CENTER - THROTTLE_DEADBAND
        return min(abs(offset) / max_off, 1.0) * MAX_VZ_DOWN

def joy_x_to_roll_target(drone_x):
    offset = apply_deadband(drone_x, JOY_X_CENTER, JOY_X_DEADBAND)
    if offset == 0:
        return 0.0
    if offset > 0:
        max_off = (4000 - JOY_X_CENTER) - JOY_X_DEADBAND
        return min(offset / max_off, 1.0) * MAX_VXY
    else:
        max_off = JOY_X_CENTER - JOY_X_DEADBAND
        return -min(abs(offset) / max_off, 1.0) * MAX_VXY

def joy_y_to_forward_target(drone_y):
    offset = apply_deadband(drone_y, JOY_Y_CENTER, JOY_Y_DEADBAND)
    if offset == 0:
        return 0.0
    if offset > 0:
        max_off = (4000 - JOY_Y_CENTER) - JOY_Y_DEADBAND
        return min(offset / max_off, 1.0) * MAX_VXY
    else:
        max_off = JOY_Y_CENTER - JOY_Y_DEADBAND
        return -min(abs(offset) / max_off, 1.0) * MAX_VXY

def spin_y_to_yaw_target(spin_y):
    offset = apply_deadband(spin_y, SPIN_Y_CENTER, SPIN_Y_DEADBAND)
    if offset == 0:
        return 0.0
    if offset > 0:
        max_off = (4000 - SPIN_Y_CENTER) - SPIN_Y_DEADBAND
        return min(offset / max_off, 1.0) * MAX_YAW_RATE
    else:
        max_off = SPIN_Y_CENTER - SPIN_Y_DEADBAND
        return -min(abs(offset) / max_off, 1.0) * MAX_YAW_RATE

def slew(current, target, max_delta):
    delta = target - current
    if delta > max_delta:
        return current + max_delta
    if delta < -max_delta:
        return current - max_delta
    return target

async def check_pre_arm_safety(drone, packet):
    if packet['power_y'] > 300:
        return False, f"Throttle not at bottom ({packet['power_y']})!"
    if abs(packet['drone_x'] - JOY_X_CENTER) > 400:
        return False, f"Joystick X off-center ({packet['drone_x']})"
    if abs(packet['drone_y'] - JOY_Y_CENTER) > 400:
        return False, f"Joystick Y off-center ({packet['drone_y']})"
    return True, "OK"

async def start_offboard_safe(drone):
    try:
        for _ in range(5):
            await drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0)
            )
            await asyncio.sleep(0.02)
        await drone.offboard.start()
        return True
    except OffboardError as e:
        print(f"  Offboard start error: {e}")
        return False
    except Exception as e:
        print(f"  Offboard start exception: {e}")
        return False

async def stop_offboard_safe(drone):
    try:
        await drone.offboard.stop()
        return True
    except Exception:
        return False

async def force_disarm(drone):
    try:
        await drone.action.disarm()
        return True
    except Exception:
        try:
            await drone.action.kill()
            return True
        except Exception:
            return False

class State:
    def __init__(self):
        self.in_air = False
        self.alt_raw = 0.0
        self.alt_baseline = None
        self.alt_rel = 0.0

st = State()

async def task_in_air(drone):
    try:
        async for v in drone.telemetry.in_air():
            st.in_air = v
    except Exception as e:
        print(f"  in_air task error: {e}")

async def task_position(drone):
    try:
        async for pos in drone.telemetry.position():
            st.alt_raw = pos.relative_altitude_m
            if st.alt_baseline is None:
                st.alt_baseline = st.alt_raw
            st.alt_rel = st.alt_raw - st.alt_baseline
    except Exception as e:
        print(f"  position task error: {e}")

def signed_bar(value, scale, width=18):
    if scale == 0:
        return ' ' * width
    norm = max(-1.0, min(1.0, value / scale))
    c = width // 2
    if norm >= 0:
        n = int(norm * (width - c - 1))
        return ' ' * c + '>' * n + ' ' * (width - c - 1 - n)
    n = int(abs(norm) * c)
    return ' ' * (c - n) + '<' * n + ' ' * (width - c - 1) + ' '

def throttle_bar(value, width=18):
    p = int(max(0, min(4000, value)) / 4000 * width)
    return '#' * p + '-' * (width - p)

def print_status(packet, vz_t, yaw_t, fwd_t, roll_t, vz, yaw, fwd, roll,
                 armed, in_air, alt_rel, mode, sw6_mode):
    print("\033[2J\033[H", end="")
    if not in_air:
        lock_status = "GROUND      "
    else:
        lock_status = "FLYING      "
    print("="*78)
    print(f" IOTROCOP TJ v4 (SITL) | Mode: {mode:<8} | SW6: {sw6_mode:<4} | "
          f"ARMED={'YES' if armed else 'NO ':<3} | IN_AIR={'YES' if in_air else 'NO '} | {lock_status}")
    base = st.alt_baseline if st.alt_baseline is not None else 0
    print(f" Altitude (relative): {alt_rel:+.2f}m  [raw={st.alt_raw:.2f}m, base={base:.2f}m]")
    print("="*78)

    print("\n STICKS (raw values):")
    print(f"   Throttle (power_y) [{packet['power_y']:5d}]  "
          f"{throttle_bar(packet['power_y'])}")
    print(f"   JOY X    (drone_x) [{packet['drone_x']:5d}]  -> ROLL")
    print(f"   JOY Y    (drone_y) [{packet['drone_y']:5d}]  -> PITCH")
    print(f"   spin_y             [{packet['spin_y']:5d}]  -> YAW")

    print("\n COMMANDS TO PX4:")
    climb = -vz
    print(f"   Climb rate  actual={climb:+.3f} m/s  "
          f"{signed_bar(climb, MAX_VZ_UP)}")
    print(f"   Yaw rate    actual={yaw:+6.1f} deg/s  "
          f"{signed_bar(yaw, MAX_YAW_RATE)}")
    print(f"   Forward     actual={fwd:+.3f} m/s  "
          f"{signed_bar(fwd, MAX_VXY)}")
    print(f"   Roll        actual={roll:+.3f} m/s  "
          f"{signed_bar(roll, MAX_VXY)}")
    print("\n" + "-"*78)
    print(" MAP: THROTTLE=climb/descend  JOY L/R=ROLL  JOY U/D=PITCH  SPIN=YAW")
    print("-"*78)

async def main():
    drone = System(mavsdk_server_address='localhost', port=50051)
    await drone.connect()

    print("\n" + "="*78)
    print(" IOTROCOP DRONE - TJ v2 (SITL - Gazebo)")
    print("="*78)

    print("  Connecting...")
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("  Connected!")
            break

    await asyncio.sleep(1.0)

    asyncio.ensure_future(task_in_air(drone))
    asyncio.ensure_future(task_position(drone))
    await asyncio.sleep(1.0)

    print("\n READY. Waiting for RC packets on UDP 5656...\n")

    armed = False
    flight_mode = 'idle'
    offboard_active = False
    last_arm = False
    last_sw6 = None
    last_print = 0.0
    ground_low_throttle_start = None

    vz_cmd = 0.0
    yaw_cmd = 0.0
    fwd_cmd = 0.0
    roll_cmd = 0.0

    while True:
        try:
            data, _ = sock.recvfrom(1024)
        except BlockingIOError:
            if offboard_active and armed:
                try:
                    await drone.offboard.set_velocity_body(
                        VelocityBodyYawspeed(fwd_cmd, roll_cmd, vz_cmd, yaw_cmd)
                    )
                except Exception:
                    pass
            await asyncio.sleep(1.0 / SETPOINT_HZ)
            continue

        packet = parse_packet(data)
        if not packet:
            continue

        raw_sw = packet['switch_states']
        arm_switch = ((raw_sw >> 12) & 1) == 1

        if arm_switch != last_arm:
            print(f"\n[SWITCH] ARM={'ON' if arm_switch else 'OFF'}\n")
            last_arm = arm_switch

        if arm_switch and not armed:
            print("\n>>> ARM requested - safety checks...")
            ok, reason = await check_pre_arm_safety(drone, packet)
            if not ok:
                print(f">>> ARM BLOCKED: {reason}\n")
                send_status("error", f"ARM blocked: {reason}")
                while arm_switch:
                    try:
                        data, _ = sock.recvfrom(1024)
                        p = parse_packet(data)
                        if p:
                            arm_switch = ((p['switch_states'] >> 12) & 1) == 1
                    except BlockingIOError:
                        pass
                    await asyncio.sleep(0.05)
                last_arm = False
                continue

            try:
                await drone.action.arm()
                armed = True
                flight_mode = 'idle'
                vz_cmd = yaw_cmd = fwd_cmd = roll_cmd = 0.0
                st.alt_baseline = st.alt_raw
                print(f">>> ARMED - altitude baseline = {st.alt_baseline:.2f}m")

                ok = await start_offboard_safe(drone)
                if ok:
                    offboard_active = True
                    print(">>> Offboard ACTIVE\n")
                    send_status("armed", "Armed + Offboard")
                else:
                    print(">>> WARNING: Offboard failed!\n")
            except Exception as e:
                print(f">>> ARM error: {e}\n")
                send_status("error", f"ARM failed: {e}")
            continue

        elif (not arm_switch) and armed:
            print("\n>>> DISARM requested")
            if st.in_air:
                print(">>> In air - emergency land first")
                if offboard_active:
                    await stop_offboard_safe(drone)
                    offboard_active = False
                try:
                    await drone.action.land()
                    print(">>> Land command sent")
                    for _ in range(40):
                        await asyncio.sleep(0.5)
                        if not st.in_air:
                            print(">>> Landed")
                            break
                except Exception as e:
                    print(f">>> Land failed: {e}")
            else:
                print(">>> On ground - direct disarm")

            if offboard_active:
                await stop_offboard_safe(drone)
                offboard_active = False
            await force_disarm(drone)
            armed = False
            flight_mode = 'idle'
            ground_low_throttle_start = None
            vz_cmd = yaw_cmd = fwd_cmd = roll_cmd = 0.0
            print(">>> Disarmed\n")
            send_status("disarmed", "Disarmed")
            continue

        if not armed:
            await asyncio.sleep(0.02)
            continue

        sw6_bits = (raw_sw >> 10) & 0x03
        sw6_mode = {0: 'MID', 1: 'TOP', 2: 'BOT'}.get(sw6_bits, 'TOP')
        if sw6_mode != last_sw6:
            print(f"\n[SW6] mode={sw6_mode}\n")
            last_sw6 = sw6_mode

        auto_takeoff_mode = (sw6_mode == 'MID')
        auto_land_mode = (sw6_mode == 'BOT')

        if auto_land_mode:
            vz_target = MAX_VZ_DOWN if st.in_air else 0.0
            yaw_target = 0.0
            fwd_target = 0.0
            roll_target = 0.0
        else:
            if auto_takeoff_mode and st.alt_rel < (AUTO_TAKEOFF_ALT - 0.05):
                vz_target = -MAX_VZ_UP
            elif auto_takeoff_mode and packet['power_y'] < (THROTTLE_CENTER - THROTTLE_DEADBAND):
                vz_target = 0.0
            else:
                vz_target = throttle_to_vz_target(packet['power_y'])
            roll_target = joy_x_to_roll_target(packet['drone_x'])
            fwd_target = joy_y_to_forward_target(packet['drone_y'])
            yaw_target = spin_y_to_yaw_target(packet['spin_y'])

        if not st.in_air:
            if vz_target > 0:
                vz_target = 0.0
            yaw_target = 0.0
            fwd_target = 0.0
            roll_target = 0.0

        vz_cmd  = slew(vz_cmd,  vz_target,  SLEW_VZ)
        yaw_cmd = slew(yaw_cmd, yaw_target, SLEW_YAW)
        fwd_cmd = slew(fwd_cmd, fwd_target, SLEW_VXY)
        roll_cmd = slew(roll_cmd, roll_target, SLEW_VXY)

        active = (abs(vz_target) > 0.001 or abs(yaw_target) > 0.5 or
                   abs(fwd_target) > 0.001 or abs(roll_target) > 0.001)
        if st.in_air and not active:
            flight_mode = 'hover'
        elif st.in_air and active:
            flight_mode = 'manual'
        else:
            flight_mode = 'ground'

        throttle_low = packet['power_y'] < (THROTTLE_CENTER - THROTTLE_DEADBAND)
        if (not st.in_air) and throttle_low and armed:
            if ground_low_throttle_start is None:
                ground_low_throttle_start = time.time()
            elif time.time() - ground_low_throttle_start > GROUND_DISARM_TIME:
                pass  # auto-disarm still disabled, fix pending (has_flown flag)
        else:
            ground_low_throttle_start = None

        if auto_land_mode and (not st.in_air) and armed:
            print("\n>>> AUTO LAND: touched down - auto-disarming\n")
            if offboard_active:
                await stop_offboard_safe(drone)
                offboard_active = False
            await force_disarm(drone)
            armed = False
            flight_mode = 'idle'
            vz_cmd = yaw_cmd = fwd_cmd = roll_cmd = 0.0
            send_status("disarmed", "Auto-landed and disarmed")
            continue

        if not offboard_active:
            ok = await start_offboard_safe(drone)
            if not ok:
                await asyncio.sleep(0.1)
                continue
            offboard_active = True

        try:
            await drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(fwd_cmd, roll_cmd, vz_cmd, yaw_cmd)
            )
        except Exception:
            pass

        now = time.time()
        if now - last_print > LOG_INTERVAL:
            print_status(packet, vz_target, yaw_target, fwd_target, roll_target,
                         vz_cmd, yaw_cmd, fwd_cmd, roll_cmd,
                         armed, st.in_air, st.alt_rel, flight_mode, sw6_mode)
            last_print = now

        await asyncio.sleep(1.0 / SETPOINT_HZ)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nShutdown")
        send_status("shutdown", "Shutdown")
