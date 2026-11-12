"""A50-21: KIOS-only independent OS-supervised fixed synthetic subprocesses.

This is deliberately NOT a general command runner, not a ROS wrapper and
not a hardware process-safety certification. Only fixed mock Python programs
can run. No user-provided executable or shell command is accepted.
"""
from __future__ import annotations
import os
import signal
import subprocess
import sys
import time

SCHEMA = 'TRUST_ROBOT_R135_A50_21_SYNTHETIC_PROCESS_SUPERVISOR_V1'
MAX_TEST_BUDGET_NS = 3_000_000_000

_FIXED_CASES = {
    'CLEAN_EXIT': 'import sys; sys.exit(0)',
    'NONZERO_EXIT': 'import sys; sys.exit(7)',
    'SLEEP': 'import time; time.sleep(10)',
    'IGNORE_TERM': (
        'import signal,time; '
        'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
        'time.sleep(10)'
    ),
    'CHILD_REMAINS': (
        'import subprocess,sys,time; '
        'subprocess.Popen([sys.executable,"-I","-c",'
        '"import time; time.sleep(10)"],'
        'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,'
        'stderr=subprocess.DEVNULL); time.sleep(0.08)'
    ),
}

class SupervisorDenied(ValueError):
    pass

def _active_group(pgid):
    """True/False, or None if process-table verification was unavailable."""
    try:
        p = subprocess.run(
            ['ps', '-eo', 'pgid=,stat='],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=1,
        )
        if p.returncode != 0:
            return None
        for line in p.stdout.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[0].isdigit():
                if int(fields[0]) == pgid and not fields[1].startswith('Z'):
                    return True
        return False
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None

def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        return False
    return True

def _stop_group(pgid, proc):
    """Never assume leader exit implies process-group shutdown."""
    for sig, grace in ((signal.SIGTERM, 0.12), (signal.SIGKILL, 0.20)):
        live = _active_group(pgid)
        if live is False:
            break
        _signal_group(pgid, sig)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if _active_group(pgid) is False:
                break
            time.sleep(0.005)
    try:
        proc.wait(timeout=0.15)
    except subprocess.TimeoutExpired:
        pass
    return proc.poll() is not None and _active_group(pgid) is False

def run_synthetic_case(case, budget_ns=2_500_000_000):
    """OS-clock parent enforces a short bound on a fixed mock child group."""
    if type(case) is not str or case not in _FIXED_CASES:
        raise SupervisorDenied('CASE_NOT_ALLOWLISTED')
    if type(budget_ns) is not int or not 0 < budget_ns <= MAX_TEST_BUDGET_NS:
        raise SupervisorDenied('BUDGET_NOT_ALLOWLISTED')

    child = None
    timeout = False
    descendant = False
    code = None
    shutdown_verified = False
    try:
        child = subprocess.Popen(
            [sys.executable, '-I', '-c', _FIXED_CASES[case]],
            cwd='/', stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic_ns() + budget_ns
        while True:
            code = child.poll()
            if code is not None:
                descendant = _active_group(child.pid) is True
                break
            if time.monotonic_ns() >= deadline:
                timeout = True
                break
            time.sleep(0.005)
    finally:
        if child is not None:
            shutdown_verified = _stop_group(child.pid, child)
            code = child.returncode

    if not shutdown_verified:
        outcome = 'DENIED_SHUTDOWN_UNVERIFIED'
    elif timeout:
        outcome = 'DENIED_DEADLINE_EXCEEDED_CLEANED'
    elif descendant:
        outcome = 'DENIED_DESCENDANT_CLEANED'
    elif code != 0:
        outcome = 'DENIED_NONZERO_CHILD_EXIT'
    else:
        outcome = 'SYNTHETIC_SUCCESS_ONLY'
    return {
        'schema': SCHEMA,
        'case': case,
        'outcome': outcome,
        'timeout_detected': timeout,
        'shutdown_verified': shutdown_verified,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
        'ros_execution': False,
        'jetson_contact': False,
    }
