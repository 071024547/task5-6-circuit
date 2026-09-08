"""Task 5-1: RC low-pass filter (R = 1 kOhm, C = 100 nF).

Run after installing PySpice + ngspice:
    python rc_lowpass.py

The script performs a transient analysis with a 1 kHz square wave and an AC
analysis for the Bode plot, then writes CSV files and PNG figures into
`figures/` next to the script.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from PySpice.Spice.Netlist import Circuit


HERE = Path(__file__).resolve().parent
FIGURE_DIR = HERE / "figures"
FIGURE_DIR.mkdir(exist_ok=True)

R = 1_000.0          # ohm
C = 100e-9           # farad
TAU = R * C
FC = 1.0 / (2.0 * math.pi * TAU)

SQ_PERIOD = 1e-3     # s
SQ_AMPLITUDE = 1.0   # V


def as_float_array(values):
    """Return a plain float ndarray from a PySpice waveform."""
    if hasattr(values, "magnitude"):
        values = values.magnitude
    return np.asarray(values, dtype=float)


def as_complex_array(values):
    """Return a plain complex ndarray from a PySpice AC waveform."""
    if hasattr(values, "magnitude"):
        values = values.magnitude
    return np.asarray(values, dtype=complex)


def print_hand_calc() -> None:
    print("=" * 70)
    print("RC 低通滤波器：理论计算")
    print("=" * 70)
    print(f"R  = {R/1000:.3f} kOhm")
    print(f"C  = {C*1e9:.1f} nF")
    print(f"tau = R * C = {TAU*1e6:.2f} us")
    print(f"fc  = 1 / (2*pi*R*C) = {FC/1000:.3f} kHz")
    print("高频增益斜率：-20 dB/decade")
    print("在 fc 处：|H| = 1/sqrt(2), 增益 = -3.01 dB, 相位 = -45 deg")


def build_circuit() -> Circuit:
    circuit = Circuit("RC low-pass filter")
    circuit.PulseVoltageSource(
        "input",
        "vin",
        circuit.gnd,
        initial_value=-SQ_AMPLITUDE,
        pulsed_value=SQ_AMPLITUDE,
        pulse_width=SQ_PERIOD / 2,
        period=SQ_PERIOD,
        rise_time=1e-6,
        fall_time=1e-6,
        dc_offset=-SQ_AMPLITUDE,
    )
    circuit.R("r1", "vin", "vout", R)
    circuit.C("c1", "vout", circuit.gnd, C)
    return circuit


def save_transient_plot(time_s, vin, vout) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("未安装 matplotlib，跳过 PNG 波形图。CSV 数据仍已保存。")
        return

    fig, ax = plt.subplots(figsize=(10, 5), dpi=110)
    ax.plot(time_s * 1e3, vin, label="Vin", linewidth=1.2)
    ax.plot(time_s * 1e3, vout, label="Vout", linewidth=1.2)
    ax.set_xlabel("t / ms")
    ax.set_ylabel("V / V")
    ax.set_title("RC Low-Pass Transient (1 kHz Square Wave)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "rc_lowpass_transient.png")
    plt.close(fig)


def save_bode_plots(freq_hz, gain_db, phase_deg) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("未安装 matplotlib，跳过 PNG 波形图。CSV 数据仍已保存。")
        return

    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=110)
    ax1.semilogx(freq_hz, gain_db, color="#0b6e4f")
    ax1.axhline(-3.0, color="gray", linestyle="--", linewidth=1)
    ax1.axvline(FC, color="crimson", linestyle="--", linewidth=1, label="fc (theory)")
    ax1.set_xlabel("f / Hz")
    ax1.set_ylabel("Gain / dB")
    ax1.set_title("RC Low-Pass Bode Magnitude")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "rc_lowpass_bode.png")
    plt.close(fig)

    fig, ax2 = plt.subplots(figsize=(10, 4), dpi=110)
    ax2.semilogx(freq_hz, phase_deg, color="#2456a6")
    ax2.set_xlabel("f / Hz")
    ax2.set_ylabel("Phase / deg")
    ax2.set_title("RC Low-Pass Bode Phase")
    ax2.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "rc_lowpass_bode_phase.png")
    plt.close(fig)

    print("PNG 已保存到:", FIGURE_DIR)


def run_transient(circuit: Circuit) -> None:
    print()
    print("=" * 70)
    print("仿真 1：方波瞬态分析 (1 kHz, +-1 V)")
    print("=" * 70)

    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    analysis = simulator.transient(step_time=1e-6, end_time=4e-3)

    time_s = as_float_array(analysis.time)
    vin = as_float_array(analysis["vin"])
    vout = as_float_array(analysis["vout"])

    csv_path = FIGURE_DIR / "rc_lowpass_transient.csv"
    np.savetxt(
        csv_path,
        np.column_stack((time_s, vin, vout)),
        delimiter=",",
        header="time_s,vin,vout",
        comments="",
    )

    settle = time_s >= 3e-3
    vin_pp = float(vin[settle].max() - vin[settle].min())
    vout_pp = float(vout[settle].max() - vout[settle].min())
    print("已保存:", csv_path)
    print(f"稳定后输入峰峰值: {vin_pp:.4f} V")
    print(f"稳定后输出峰峰值: {vout_pp:.4f} V")
    print("输出为指数充放电波形；波形图见 rc_lowpass_transient.png。")

    save_transient_plot(time_s, vin, vout)


def run_ac() -> None:
    print()
    print("=" * 70)
    print("仿真 2：AC 扫描 / 波特图 (10 Hz ... 1 MHz)")
    print("=" * 70)

    circuit = Circuit("RC low-pass AC")
    circuit.SinusoidalVoltageSource("input", "vin", circuit.gnd, amplitude=1.0)
    circuit.R("r1", "vin", "vout", R)
    circuit.C("c1", "vout", circuit.gnd, C)

    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    ac = simulator.ac(
        start_frequency=10,
        stop_frequency=1e6,
        number_of_points=61,
        variation="dec",
    )

    freq = as_float_array(ac.frequency)
    vin = as_complex_array(ac["vin"])
    vout = as_complex_array(ac["vout"])
    with np.errstate(divide="ignore", invalid="ignore"):
        transfer = vout / vin
        gain_db = 20.0 * np.log10(np.maximum(np.abs(transfer), 1e-12))
        phase_deg = np.degrees(np.angle(transfer))

    csv_path = FIGURE_DIR / "rc_lowpass_bode.csv"
    np.savetxt(
        csv_path,
        np.column_stack((freq, gain_db, phase_deg)),
        delimiter=",",
        header="freq_hz,gain_db,phase_deg",
        comments="",
    )
    print("已保存:", csv_path)

    idx = int(np.argmin(np.abs(gain_db - (-3.0))))
    f3db_sim = float(freq[idx])
    print(f"理论 fc          : {FC:.3f} Hz")
    print(f"最近仿真 -3 dB 点: {f3db_sim:.3f} Hz (表格中最接近的一个扫描点)")

    table = [
        ("截止频率 fc", f"{FC:.3f} Hz", f"{f3db_sim:.3f} Hz"),
        ("时间常数 tau", f"{TAU*1e6:.2f} us", "由瞬态指数曲线读取"),
    ]
    print()
    print("理论值 vs 仿真值（运行后回填到 README）")
    for name, theoretical, simulated in table:
        print(f"{name:<18} | 理论 {theoretical:<14} | 仿真 {simulated}")

    save_bode_plots(freq, gain_db, phase_deg)


def main() -> None:
    print_hand_calc()
    circuit = build_circuit()
    run_transient(circuit)
    run_ac()
    print()
    print("完成。将表格中的仿真值填入 README 后即可使用。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "仿真失败。请确认已安装 PySpice 且 ngspice 可执行文件在 PATH 中。\n"
            f"原始错误: {exc}"
        ) from exc
