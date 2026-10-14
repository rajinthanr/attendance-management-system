#!/usr/bin/env python3
"""Draw the measured battery-current graphs shown in the top-level README.

Reads the TBS1052C captures in this folder through Firmware/docs/waveforms.py
(1 ohm shunt in the battery's negative lead, each capture's DC offset removed)
and writes, next to this script:

    power_wakeup.png        TEK00005  one wake-up measurement of the reader
    power_card_tap.png      TEK00006  a card tap: read, buzz, LED
    power_false_wakeup.png  TEK00007  a false wake-up: empty poll, re-arm
    power_idle.png          what the 108 uA idle current is made of

    python3 readme_plots.py

Needs numpy and matplotlib.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Firmware" / "docs"))
import waveforms  # noqa: E402

LINE = "#2a78d6"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
SHADE = "#eef4fc"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def trace(cap, a, b, smooth):
    """(t in ms, mA) between a and b seconds, offset removed, moving average of `smooth` points."""
    t = np.array(cap.t)
    i = np.array(cap.i) - cap.offset
    keep = (t >= a) & (t < b)
    t, i = t[keep] * 1000.0, i[keep]
    if smooth > 1:
        i = np.convolve(i, np.ones(smooth) / smooth, mode="same")
    return t, i


def axes(title, xlabel="time (ms)"):
    fig, ax = plt.subplots(figsize=(10, 3.6), layout="constrained")
    ax.grid(True, axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("battery current (mA)")
    return fig, ax


def band(ax, a, b, text, y, ha="center"):
    ax.axvspan(a, b, color=SHADE, zorder=0, lw=0)
    x = {"center": (a + b) / 2, "left": a, "right": b}[ha]
    ax.text(x, y, text, ha=ha, va="top", color=INK, fontsize=9, linespacing=1.3)


def note(fig, text):
    fig.supxlabel(text, x=0.01, ha="left", color=INK2, fontsize=8)


def save(fig, name):
    fig.savefig(HERE / name, dpi=150)
    plt.close(fig)
    print("wrote", HERE / name)


def main():
    m = waveforms.measure()
    src = f"Tektronix TBS1052C, 1 Ω shunt in the battery lead, measured {waveforms.MEASURED_ON}"

    # One wake-up measurement
    t, i = trace(m["wu"], -1.0e-3, 0.6e-3, 5)
    fig, ax = axes(f"One reader wake-up measurement (every 100 ms): {m['q_wu']:.1f} µC, "
                   f"{m['q_wu'] * 10:.0f} µA on average", "time (ms)")
    ax.plot(t, i, color=LINE, lw=1.5)
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-5, 105)
    band(ax, -0.65, -0.25, f"oscillator start\n{m['wu_osc_ma']:.0f} mA, 0.4 ms", 100)
    band(ax, -0.25, -0.03, f"plateau\n{m['wu_plateau_ma']:.1f} mA", 100)
    ax.annotate(f"antenna measured\n{m['wu_spike_peak']:.0f} mA peak, {m['wu_spike_us']:.0f} µs",
                xy=(0.02, m["wu_spike_peak"]), xytext=(0.18, 80), color=INK, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.text(-0.98, 30, "a few µA\nbetween\nmeasurements", color=INK2, fontsize=9, va="top")
    note(fig, src + " (TEK00005)")
    save(fig, "power_wakeup.png")

    # Card tap
    t, i = trace(m["tap"], -5e-3, 128e-3, 3)
    fig, ax = axes("A card tap: one read, one buzz, then the green LED")
    ax.plot(t, i, color=LINE, lw=1.2)
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-10, 290)
    band(ax, 0, 12.3, f"RF field on\n{m['read_ma']:.0f} mA\n{m['read_ms']:.1f} ms", 285, "left")
    band(ax, 12.3, 62.6, f"vibration motor\n{m['buzz_ma']:.0f} mA average, {m['buzz_ms']:.0f} ms\n"
         f"{m['q_buzz'] / 1000:.2f} mC", 285)
    band(ax, 70, 128, f"reader ready + green LED\n{m['ready_led_ma']:.1f} mA", 285)
    note(fig, src + f" (TEK00006). Read {m['q_read'] / 1000:.2f} mC, buzz "
         f"{m['q_buzz'] / 1000:.2f} mC; the whole tap with its LED pattern is 10.3 mC (2.8 µAh).")
    save(fig, "power_card_tap.png")

    # False wake-up
    t, i = trace(m["fw"], -5e-3, 110e-3, 3)
    fig, ax = axes("A false wake-up: one empty poll, then back to wake-up mode")
    ax.plot(t, i, color=LINE, lw=1.2)
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-10, 260)
    ax.axvspan(0, 6.0, color=SHADE, zorder=0, lw=0)
    ax.text(7.5, 240, f"empty poll: field on, no card\n{m['empty_ma']:.0f} mA for {m['empty_ms']:.1f} ms"
            f" ({m['q_false'] / 1000:.2f} mC)", va="top", color=INK, fontsize=9)
    ax.annotate("measurement that\nwoke the MCU", xy=(-2.4, 85), xytext=(-4.5, 150), color=INK,
                fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.annotate("next wake-up\nmeasurement", xy=(105.3, 88), xytext=(92, 150), color=INK,
                fontsize=9, ha="center", arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.text(55, 60, f"re-armed {m['off_to_rearm']:.1f} ms after the field goes off;\n"
            f"next measurement {m['rearm_to_next']:.0f} ms later", ha="center", color=INK, fontsize=9)
    note(fig, src + " (TEK00007)")
    save(fig, "power_false_wakeup.png")

    # Idle current breakdown (power report, section 3)
    parts = [("Reader wake-up mode (one measurement / 100 ms)", m["q_wu"] * 10),
             ("Heartbeat LED (10 ms every 5 s)", 2.77e3 * 10 / 5000),
             ("MCU in Stop 2 + RTC, board static draw", 3.30),
             ("MCU wake-ups (0.4 / s)", 0.20),
             ("Battery sample (every 10 s)", 0.18)]
    total = sum(v for _, v in parts)
    fig, ax = plt.subplots(figsize=(10, 2.9), layout="constrained")
    names = [n for n, _ in parts][::-1]
    vals = [v for _, v in parts][::-1]
    ax.barh(names, vals, color=LINE, height=0.55)
    for y, v in enumerate(vals):
        ax.text(v + 1, y, f"{v:.2f} µA", va="center", color=INK, fontsize=9)
    ax.set_xlim(0, 115)
    ax.set_xlabel("battery current (µA)")
    ax.grid(True, axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0, labelcolor=INK)
    ax.set_title(f"Switched on and waiting for cards: {total:.0f} µA in total", loc="left",
                 fontsize=11, fontweight="bold")
    save(fig, "power_idle.png")


if __name__ == "__main__":
    main()
