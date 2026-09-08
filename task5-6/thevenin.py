"""Task 5-2: Thevenin theorem verification.

Two-resistor source network:
    VS = 12 V, R1 = 2.7 kOhm, R2 = 3.3 kOhm, port a-b, RL = 1 kOhm.

Run after installing PySpice + ngspice:
    python thevenin.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from PySpice.Spice.Netlist import Circuit


HERE = Path(__file__).resolve().parent
FIGURE_DIR = HERE / "figures"
FIGURE_DIR.mkdir(exist_ok=True)

VS = 12.0          # V
R1 = 2_700.0       # ohm
R2 = 3_300.0       # ohm
RL = 1_000.0       # ohm
RSHORT = 1e-9      # near-short resistor used to measure Isc


def hand_calc():
    voc = VS * R2 / (R1 + R2)
    isc = VS / R1
    rth = voc / isc
    i_load = voc / (rth + RL)
    v_load = i_load * RL
    return voc, isc, rth, i_load, v_load


def print_hand_calc(voc, isc, rth, i_load, v_load):
    print("=" * 70)
    print("戴维南定理：理论计算")
    print("=" * 70)
    print(f"V_oc = VS * R2 / (R1 + R2) = {voc:.4f} V")
    print(f"I_sc = VS / R1 = {isc*1000:.4f} mA")
    print(f"R_th = V_oc / I_sc = {rth/1000:.4f} kOhm = R1||R2")
    print(f"接 RL={RL/1000:.2f} kOhm 后:")
    print(f"  I_load = V_oc / (R_th + RL) = {i_load*1000:.4f} mA")
    print(f"  V_load = I_load * RL = {v_load:.4f} V")


def node_v(op, node):
    """Convert a single PySpice operating-point value to float volts."""
    value = op[node]
    return float(np.asarray(value).reshape(-1)[0])


def build_original(with_load=True):
    circuit = Circuit("Original two-resistor network")
    circuit.V("vs", "vdd", circuit.gnd, VS)
    circuit.R("r1", "vdd", "a", R1)
    circuit.R("r2", "a", circuit.gnd, R2)
    if with_load:
        circuit.R("rl", "a", circuit.gnd, RL)
    return circuit


def simulate_original_with_load():
    circuit = build_original(with_load=True)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    op = simulator.operating_point()
    v_load = node_v(op, "a")
    i_load = v_load / RL
    return v_load, i_load


def simulate_open_circuit():
    circuit = build_original(with_load=False)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    op = simulator.operating_point()
    return node_v(op, "a")


def simulate_short_circuit():
    circuit = Circuit("Short-circuit measurement")
    circuit.V("vs", "vdd", circuit.gnd, VS)
    circuit.R("r1", "vdd", "a", R1)
    circuit.R("r2", "a", circuit.gnd, R2)
    circuit.R("rshort", "a", circuit.gnd, RSHORT)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    op = simulator.operating_point()
    v_short = node_v(op, "a")
    return v_short / RSHORT


def simulate_thevenin_equivalent():
    circuit = Circuit("Thevenin equivalent with load")
    circuit.V("vth", "vth_node", circuit.gnd, VS * R2 / (R1 + R2))
    circuit.R("rth", "vth_node", "a_eq", R1 * R2 / (R1 + R2))
    circuit.R("rl", "a_eq", circuit.gnd, RL)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    op = simulator.operating_point()
    v_load = node_v(op, "a_eq")
    i_load = v_load / RL
    return v_load, i_load


def main():
    voc_t, isc_t, rth_t, i_load_t, v_load_t = hand_calc()
    print_hand_calc(voc_t, isc_t, rth_t, i_load_t, v_load_t)

    print()
    print("=" * 70)
    print("PySpice 仿真")
    print("=" * 70)

    v_oc = simulate_open_circuit()
    i_sc = simulate_short_circuit()
    r_th = v_oc / i_sc

    v_orig, i_orig = simulate_original_with_load()
    v_eq, i_eq = simulate_thevenin_equivalent()

    rows = [
        ("V_oc / V", voc_t, v_oc),
        ("I_sc / mA", isc_t * 1000, i_sc * 1000),
        ("R_th / kOhm", rth_t / 1000, r_th / 1000),
        ("原电路 V_load / V", v_load_t, v_orig),
        ("原电路 I_load / mA", i_load_t * 1000, i_orig * 1000),
        ("等效电路 V_load / V", v_load_t, v_eq),
        ("等效电路 I_load / mA", i_load_t * 1000, i_eq * 1000),
    ]

    print()
    print("理论值 vs 仿真值（运行后回填到 README）")
    print(f"{'项目':<22} | {'理论':>10} | {'仿真':>10} | {'偏差':>9}")
    print("-" * 62)
    for name, theory, sim in rows:
        delta = abs(sim - theory)
        print(f"{name:<22} | {theory:>10.4f} | {sim:>10.4f} | {delta:>8.2e}")

    csv_path = FIGURE_DIR / "thevenin_results.csv"
    np.savetxt(
        csv_path,
        np.array([v_oc, i_sc, r_th, v_orig, i_orig, v_eq, i_eq]),
        delimiter=",",
        header=(
            "v_oc_v,i_sc_a,r_th_ohm,"
            "v_load_original_v,i_load_original_a,"
            "v_load_thevenin_v,i_load_thevenin_a"
        ),
        comments="",
    )
    print()
    print("已保存:", csv_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "仿真失败。请确认已安装 PySpice 且 ngspice 可执行文件在 PATH 中。\n"
            f"原始错误: {exc}"
        ) from exc
