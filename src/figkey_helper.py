"""Shared helper for the ring network diagrams: numbered labels on the ring and a
readable key underneath, so the figure stays legible at text width in the thesis."""
import numpy as np
import matplotlib.pyplot as plt

FIG_W = 7.6          # inches; close to the thesis text width so fonts print near their set size
TOPN = 10            # labelled Acts per outer layer
COLS = 3
LINE_H = 0.118       # inches per key line at 6.8 pt
LEG_H = 0.95
HEADER_COLORS = {"SG1": "#1a1a1a", "SG2": "#555555", "SG3": "#4a3d8f", "SG4": "#8f3e63", "SG5": "#8a6c14"}


def make_fig(n_labelled, n_layers_with_headers):
    lines = n_labelled + n_layers_with_headers
    rows = -(-lines // COLS)
    key_h = rows * LINE_H + LEG_H + 0.35
    fig = plt.figure(figsize=(FIG_W, FIG_W + key_h), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[FIG_W, key_h], hspace=0.0,
                          left=0.01, right=0.99, top=0.995, bottom=0.005)
    ax = fig.add_subplot(gs[0])
    keyax = fig.add_subplot(gs[1])
    keyax.axis("off")
    keyax.set_xlim(0, FIG_W)
    keyax.set_ylim(0, key_h)
    keyax._key_h = key_h
    return fig, ax, keyax


def _short(name, n=34):
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


def finish(fig, ax, keyax, pos, seed, sg1, tops, legend_elems, out_path, surface):
    """tops: list of (layer_name, list_of_dicts_with_act_and_combined_score)."""
    key_h = keyax._key_h
    ax.text(*pos[seed], "Seed", fontsize=6, color="white", ha="center", va="center",
            fontweight="bold", zorder=10)
    entries = []  # (text, colour, is_header)
    n = 0
    # SG1: number in angular order so numbers are easy to find
    sg1_sorted = sorted(sg1, key=lambda a: np.arctan2(pos[a["act"]][1], pos[a["act"]][0]))
    entries.append((f"SG1 first-layer Acts (all {len(sg1)})", HEADER_COLORS["SG1"], True))
    for i, a in enumerate(sg1_sorted):
        n += 1
        x, y = pos[a["act"]]
        ang = np.arctan2(y, x)
        r = 12 if i % 2 == 0 else 21
        ax.annotate(str(n), (x, y), xytext=(r * np.cos(ang), r * np.sin(ang)), textcoords="offset points",
                    fontsize=6.5, fontweight="bold", color=HEADER_COLORS["SG1"], ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85), zorder=8)
        entries.append((f"{n}  {_short(a['act'])}", HEADER_COLORS["SG1"], False))
    for name, lst in tops:
        col = HEADER_COLORS.get(name, "#333333")
        entries.append((f"{name}: top {TOPN} by connection score", col, True))
        for c in lst[:TOPN]:
            n += 1
            x, y = pos[c["act"]]
            ang = np.arctan2(y, x)
            ax.annotate(str(n), (x, y), xytext=(9 * np.cos(ang), 9 * np.sin(ang)), textcoords="offset points",
                        fontsize=6.5, fontweight="bold", color=col, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec=col, lw=0.4, alpha=0.9), zorder=8)
            entries.append((f"{n}  {_short(c['act'])} ({c['combined_score']})", col, False))
    keyax.legend(handles=legend_elems, loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=3,
                 frameon=False, fontsize=6.6, labelspacing=0.5, columnspacing=1.2, handletextpad=0.3)
    per_col = -(-len(entries) // COLS)
    colw = FIG_W / COLS
    for k, (txt, col, hdr) in enumerate(entries):
        ci, ri = divmod(k, per_col)
        keyax.text(ci * colw + 0.06, key_h - LEG_H - 0.1 - ri * LINE_H, txt, fontsize=6.6, color=col,
                   fontweight="bold" if hdr else "normal", ha="left", va="top")
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(surface)
    fig.savefig(str(out_path), facecolor=surface)
    fig.savefig(str(out_path).replace(".png", ".pdf"), facecolor=surface)
    print(f"Saved -> {out_path}")
