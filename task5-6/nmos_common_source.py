"""Task 5-3: NMOS common-source amplifier.

Given by the assignment:
    VDD = 5 V, Rg1 = 60 kOhm, Rg2 = 40 kOhm, Rd = 2 kOhm
    NMOS: K = 0.8 mA/V^2, V_th = 1 V, lambda = 0.02 /V
    Input: Vi = 10 mV, 1 kHz sine

The coupling capacitor Cb1 is set to 1 uF. Its reactance at 1 kHz is about
159 ohm, much smaller than Rg1 || Rg2 = 24 kOhm, so it is "large enough".

Run after installing PySpice + ngspice:
    python nmos_common_source.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from PySpice.Spice.Netlist import Circuit


HERE = Path(__file__).resolve().parent
FIGURE_DIR = HERE / "figures"
FIGURE_DIR.mkdir(exist_ok=True)

VDD = 5.0
RG1 = 60_000.0
RG2 = 40_000.0
RD = 2_000.0
CB1 = 1e-6

K = 0.8e-3       # A/V^2 in the course formula
KP_MODEL = 2 * K  # SPICE Level-1 uses Id = KP/2*(W/L)*(Vov)^2
VTH = 1.0
LAMBDA = 0.02

VI_AMP = 10e-3    # V
FI = 1_000.0      # Hz


def print_hand_calc():
    vg = VDD * RG2 / (RG1 + RG2)
    vgs = vg
    vov = vgs - VTH

    print("=" * 70)
    print("NMOS 共源放大器：手算")
    print("=" * 70)
    print(f"VG = VDD*Rg2/(Rg1+Rg2) = {vg:.4f} V")
    print(f"VGS = VG - 0 = {vgs:.4f} V")
    print(f"Vov = VGS - Vth = {vov:.4f} V")
    print()
    print("先忽略 lambda 判断工作区:")
    id_0 = K * vov * vov
    vds_0 = VDD - id_0 * RD
    print(f"  ID = K*Vov^2 = {id_0*1000:.4f} mA")
    print(f"  VDS = VDD - ID*Rd = {vds_0:.4f} V")
    print(f"  饱和条件 VDS > Vov: {vds_0:.3f} > {vov:.3f}，成立")

    print()
    print("再计入 lambda=0.02 /V 精算:")
    a = K * vov * vov
    id_sat = a * (1 + LAMBDA * VDD) / (1 + LAMBDA * RD * a)
    vds_sat = VDD - id_sat * RD
    gm = 2 * K * vov * (1 + LAMBDA * vds_sat)
    ro = 1 / (LAMBDA * id_sat)
    r_out = RD * ro / (RD + ro)
    av = -gm * r_out

    print(f"  ID = K*Vov^2*(1+lambda*VDS) = {id_sat*1000:.4f} mA")
    print(f"  VDS = VDD - ID*Rd = {vds_sat:.4f} V")
    print(f"  gm = 2*K*Vov*(1+lambda*VDS) = {gm*1000:.4f} mS")
    print(f"  ro = 1/(lambda*ID) = {ro/1000:.3f} kOhm")
    print(f"  Av = -gm*(Rd||ro) = {av:.4f} V/V")
    return vg, id_sat, vds_sat, gm, ro, av


def as_float_array(values):
    if hasattr(values, "magnitude"):
        values = values.magnitude
    return np.asarray(values, dtype=float)


def as_complex_array(values):
    if hasattr(values, "magnitude"):
        values = values.magnitude
    return np.asarray(values, dtype=complex)


def node_v(value):
    return float(np.asarray(value).reshape(-1)[0])


def add_bias_network(circuit: Circuit) -> None:
    circuit.V("dd", "vdd", circuit.gnd, VDD)
    circuit.R("rg1", "vdd", "gate", RG1)
    circuit.R("rg2", "gate", circuit.gnd, RG2)
    circuit.R("rd", "vdd", "drain", RD)


def add_mosfet(circuit: Circuit) -> None:
    circuit.Mosfet(
        "q1",
        "drain",
        "gate",
        circuit.gnd,
        circuit.gnd,
        model="nmos1",
        w=1e-6,
        l=1e-6,
    )
    circuit.model(
        "nmos1",
        "nmos",
        LEVEL=1,
        VTO=VTH,
        KP=KP_MODEL,
        LAMBDA=LAMBDA,
    )


def build_bias_circuit() -> Circuit:
    circuit = Circuit("NMOS DC bias")
    add_bias_network(circuit)
    add_mosfet(circuit)
    return circuit


def build_full_circuit() -> Circuit:
    circuit = Circuit("NMOS common-source amplifier")
    add_bias_network(circuit)
    circuit.SinusoidalVoltageSource(
        "input",
        "vin",
        circuit.gnd,
        amplitude=VI_AMP,
        frequency=FI,
    )
    circuit.C("cb1", "vin", "gate", CB1)
    add_mosfet(circuit)
    return circuit


def run_operating_point():
    print()
    print("=" * 70)
    print("仿真 1：直流工作点 OP")
    print("=" * 70)
    circuit = build_bias_circuit()
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    op = simulator.operating_point()

    vg = node_v(op["gate"])
    vd = node_v(op["drain"])
    vgs = vg
    vds = vd
    id_sim = (VDD - vd) / RD
    vov = vgs - VTH

    gm_sim = 2 * K * vov * (1 + LAMBDA * vds)
    ro_sim = 1 / (LAMBDA * id_sim)
    r_out_sim = RD * ro_sim / (RD + ro_sim)
    av_op_sim = -gm_sim * r_out_sim

    print(f"V_GS = {vgs:.6f} V")
    print(f"I_D  = {id_sim*1000:.6f} mA  (由 (VDD-Vd)/Rd 计算)")
    print(f"V_DS = {vds:.6f} V")
    print(f"饱和区判断: V_DS={vds:.4f} V > Vov={vov:.4f} V -> 工作在饱和区")
    print(f"gm = {gm_sim*1000:.6f} mS, ro = {ro_sim/1000:.3f} kOhm")
    return vgs, id_sim, vds, gm_sim, ro_sim, av_op_sim


def run_transient():
    print()
    print("=" * 70)
    print("仿真 2：瞬态波形 (Vi = 10 mV, 1 kHz)")
    print("=" * 70)

    circuit = build_full_circuit()
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    analysis = simulator.transient(step_time=1e-6, end_time=10e-3)

    time_s = as_float_array(analysis.time)
    vin = as_float_array(analysis["vin"])
    vgate = as_float_array(analysis["gate"])
    vout = as_float_array(analysis["drain"])

    csv_path = FIGURE_DIR / "nmos_transient.csv"
    np.savetxt(
        csv_path,
        np.column_stack((time_s, vin, vgate, vout)),
        delimiter=",",
        header="time_s,vin,vgate,vout",
        comments="",
    )
    print("已保存:", csv_path)

    mask = (time_s >= 8e-3) & (time_s < 10e-3)
    t = time_s[mask]
    x = vin[mask] - vin[mask].mean()
    y = vout[mask] - vout[mask].mean()

    dt = float(np.median(np.diff(t)))
    n = len(t)
    freq = np.fft.fftfreq(n, dt)
    fx = np.fft.fft(x)
    fy = np.fft.fft(y)
    idx = int(np.argmin(np.abs(freq - FI)))
    amp_in = 2.0 * abs(fx[idx]) / n
    amp_out = 2.0 * abs(fy[idx]) / n
    phase_deg = float(np.degrees(np.angle(fy[idx]) - np.angle(fx[idx])))
    if phase_deg > 0:
        phase_deg -= 360.0
    gain_tran = amp_out / amp_in

    print(f"最后 2 ms 输入幅度: {amp_in*1000:.4f} mV")
    print(f"最后 2 ms 输出幅度: {amp_out*1000:.4f} mV")
    print(f"瞬态测得的 |Av|: {gain_tran:.4f} V/V")
    print(f"输入输出相位差: {phase_deg:.1f} deg（约 -180 deg，反相）")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5), dpi=110)
        ax.plot(t * 1e3, x * 1000, label="Vin AC component / mV", linewidth=1.1)
        ax.plot(t * 1e3, y * 1000, label="Vout AC component / mV", linewidth=1.1)
        ax.set_xlabel("t / ms")
        ax.set_ylabel("amplitude")
        ax.set_title("NMOS CS Amplifier: 1 kHz small-signal response")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGURE_DIR / "nmos_transient.png")
        plt.close(fig)
        print("PNG 已保存:", FIGURE_DIR / "nmos_transient.png")
    except Exception as exc:
        print(f"PNG 生成失败，已跳过。CSV 已保存。原始错误: {exc}")

    return gain_tran


def run_ac():
    print()
    print("=" * 70)
    print("仿真 3：AC 扫描（在 1 kHz 处读增益）")
    print("=" * 70)

    circuit = build_full_circuit()
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    ac = simulator.ac(
        start_frequency=0.1,
        stop_frequency=1e6,
        number_of_points=71,
        variation="dec",
    )

    freq = as_float_array(ac.frequency)
    vin_ac = as_complex_array(ac["vin"])
    vgate_ac = as_complex_array(ac["gate"])
    vout_ac = as_complex_array(ac["drain"])

    idx = int(np.argmin(np.abs(freq - FI)))
    transfer = vout_ac / vin_ac
    av_ac = transfer[idx]
    gain_db = 20 * np.log10(np.abs(transfer))

    print(f"1 kHz 处 Vout/Vin = {av_ac.real:+.4f} + j{av_ac.imag:+.4f}")
    print(f"1 kHz 处增益 = {av_ac.real:.4f} V/V（实部约为负数，表示反相）")
    print(f"1 kHz 处 Vgate/Vin = {abs(vgate_ac[idx]/vin_ac[idx]):.6f}（耦合电容影响）")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5), dpi=110)
        ax.semilogx(freq, gain_db)
        ax.axvline(FI, color="crimson", linestyle="--", label="1 kHz")
        ax.set_xlabel("f / Hz")
        ax.set_ylabel("Gain / dB")
        ax.set_title("NMOS Common-Source AC Response")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURE_DIR / "nmos_ac.png")
        plt.close(fig)
        print("PNG 已保存:", FIGURE_DIR / "nmos_ac.png")
    except Exception as exc:
        print(f"PNG 生成失败，已跳过。原始错误: {exc}")

    return av_ac.real


def print_comparison(vgs_h, id_h, vds_h, gm_h, ro_h, av_h, op_data, av_tran, av_ac):
    vgs_s, id_s, vds_s, gm_s, ro_s, _ = op_data
    print()
    print("=" * 70)
    print("理论值 vs 仿真值（运行后回填到 README）")
    print("=" * 70)
    rows = [
        ("V_GS / V", vgs_h, vgs_s),
        ("I_D / mA", id_h * 1000, id_s * 1000),
        ("V_DS / V", vds_h, vds_s),
        ("gm / mS", gm_h * 1000, gm_s * 1000),
        ("ro / kOhm", ro_h / 1000, ro_s / 1000),
        ("Av（AC 仿真）", av_h, av_ac),
        ("Av 幅度（瞬态 FFT）", abs(av_h), av_tran),
    ]
    print(f"{'项目':<14} | {'理论':>10} | {'仿真':>10} | {'偏差':>9}")
    print("-" * 52)
    for name, theory, sim in rows:
        delta = abs(sim - theory)
        print(f"{name:<14} | {theory:>10.4f} | {sim:>10.4f} | {delta:>8.2e}")


def main():
    vg, id_h, vds_h, gm_h, ro_h, av_h = print_hand_calc()
    op_data = run_operating_point()
    av_tran = run_transient()
    av_ac = run_ac()
    print_comparison(vg, id_h, vds_h, gm_h, ro_h, av_h, op_data, av_tran, av_ac)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "仿真失败。请确认已安装 PySpice 且 ngspice 可执行文件在 PATH 中。\n"
            f"原始错误: {exc}"
        ) from exc
