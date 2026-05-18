import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Use a clean style
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['DejaVu Serif', 'Times New Roman', 'Times'],
    'font.size': 10,
    'axes.unicode_minus': False,
})

# ============================================================
# Colors
# ============================================================
C_DATA  = '#2166AC'   # blue - data
C_NOISE = '#B2182B'   # red - noise
C_DDPM  = '#F4A582'   # light red/orange - DDPM
C_DDIM  = '#4393C3'   # light blue - DDIM
C_OBJ   = '#4DAF4A'   # green - objective
C_ARROW = '#666666'
C_LABEL = '#222222'

fig = plt.figure(figsize=(7.5, 8.5))
fig.patch.set_facecolor('white')

# ============================================================
# Layout grid: 2 cols × 3 rows
# ============================================================
gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.30,
                      left=0.08, right=0.97, bottom=0.06, top=0.97)

ax_fwd  = fig.add_subplot(gs[0, :])    # (a) Forward diffusion - full width
ax_ddpm = fig.add_subplot(gs[1, 0])    # (b) DDPM reverse
ax_ddim = fig.add_subplot(gs[1, 1])    # (c) DDIM reverse
ax_traj = fig.add_subplot(gs[2, :])    # (d) Trajectory comparison - full width

for ax in [ax_fwd, ax_ddpm, ax_ddim, ax_traj]:
    ax.set_facecolor('white')

# ============================================================
# Helper: draw distribution circle
# ============================================================
def draw_circle(ax, cx, cy, color, label='', radius=0.30, alpha=0.85,
                ec='white', lw=1.2, fontsize=10):
    circle = plt.Circle((cx, cy), radius, color=color, alpha=alpha,
                        ec=ec, linewidth=lw, zorder=5)
    ax.add_patch(circle)
    if label:
        ax.text(cx, cy, label, ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color='white', zorder=7)

def draw_arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=1.8, style='arc3,rad=0.0'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color,
                                connectionstyle=style, lw=lw),
                zorder=3)

# ============================================================
# (a) Forward diffusion process
# ============================================================
N = 7
x_pos = np.linspace(0, N-1, N)
y0 = 0.5

draw_circle(ax_fwd, x_pos[0], y0, C_DATA,  r'$x_0$',    radius=0.30, fontsize=10)
for i in range(1, N-1):
    t = i / (N-1)
    blend = (1-t) * np.array([0.130, 0.400, 0.675]) + t * np.array([0.698, 0.094, 0.169])
    draw_circle(ax_fwd, x_pos[i], y0, blend, f'$x_{{{i}}}$', radius=0.26, fontsize=9)
draw_circle(ax_fwd, x_pos[-1], y0, C_NOISE, r'$x_T$',   radius=0.30, fontsize=10)

for i in range(N-1):
    draw_arrow(ax_fwd, x_pos[i]+0.30, y0, x_pos[i+1]-0.30, y0, C_ARROW, lw=1.5)

# Label: q(x_t|x_{t-1})
ax_fwd.text(x_pos[3], y0 + 0.65, r'$q(x_t | x_{t-1})$', fontsize=10,
            color=C_LABEL, ha='center', style='italic', alpha=0.7)

# Noise injection arrows
for i in range(1, N):
    ax_fwd.annotate('', xy=(x_pos[i], y0+0.40), xytext=(x_pos[i], y0+0.08),
                    arrowprops=dict(arrowstyle='->', color=C_NOISE, lw=1.0, alpha=0.45),
                    zorder=2)
    if i % 2 == 0:
        ax_fwd.text(x_pos[i]+0.08, y0+0.48, r'$\epsilon_t$', fontsize=7,
                    color=C_NOISE, ha='center', alpha=0.55)

# Objective label on the side
ax_fwd.text(x_pos[-1]+0.55, y0, r'$\min_\theta$' + '\n' + r'$L_{\mathrm{simple}}$',
            fontsize=10, color=C_LABEL, ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFDE7',
                      edgecolor=C_OBJ, alpha=0.7))

ax_fwd.set_xlim(-0.6, N+0.8)
ax_fwd.set_ylim(-0.6, 1.5)
ax_fwd.set_aspect('equal')
ax_fwd.axis('off')
ax_fwd.set_title('(a) Forward diffusion process', loc='left',
                 fontsize=11, fontweight='bold', pad=6)

# ============================================================
# (b) DDPM reverse (Markovian, stochastic)
# ============================================================
y_ddpm = 0.5
draw_circle(ax_ddpm, x_pos[-1], y_ddpm, C_NOISE, r'$x_T$', radius=0.28, fontsize=9)
for i in range(1, N-1):
    idx = N-1-i
    t = i / (N-1)
    blend = (1-t) * np.array([0.957, 0.647, 0.510]) + t * np.array([0.698, 0.094, 0.169])
    draw_circle(ax_ddpm, x_pos[idx], y_ddpm, blend, f'$x_{{{idx}}}$', radius=0.24, fontsize=8)
draw_circle(ax_ddpm, x_pos[0], y_ddpm, C_DATA, r'$x_0$', radius=0.28, fontsize=9)

for i in range(N-1):
    draw_arrow(ax_ddpm, x_pos[N-1-i]-0.28, y_ddpm, x_pos[N-2-i]+0.28, y_ddpm, C_DDPM, lw=1.5)

ax_ddpm.text(x_pos[3], y_ddpm+0.65, r'$p_\theta(x_{t-1}|x_t)$', fontsize=9,
             color=C_LABEL, ha='center', style='italic', alpha=0.7)

# Stochastic noise
for i in range(1, N-1):
    ax_ddpm.annotate('', xy=(x_pos[N-1-i], y_ddpm-0.45), xytext=(x_pos[N-1-i], y_ddpm-0.12),
                    arrowprops=dict(arrowstyle='->', color=C_DDPM, lw=0.9, alpha=0.45),
                    zorder=2)
    if i % 2 == 0:
        ax_ddpm.text(x_pos[N-1-i], y_ddpm-0.60, r'$z\sim\mathcal{N}$', fontsize=6,
                    color=C_DDPM, ha='center', alpha=0.6)

ax_ddpm.set_xlim(-0.5, N+0.3)
ax_ddpm.set_ylim(-0.7, 1.5)
ax_ddpm.set_aspect('equal')
ax_ddpm.axis('off')
ax_ddpm.set_title('(b) DDPM: Markovian, stochastic', loc='left',
                  fontsize=11, fontweight='bold', pad=6)

# ============================================================
# (c) DDIM reverse (non-Markovian, deterministic, skip-step)
# ============================================================
y_ddim = 0.5
draw_circle(ax_ddim, x_pos[-1], y_ddim, C_NOISE, r'$x_T$', radius=0.28, fontsize=9)
draw_circle(ax_ddim, x_pos[0],  y_ddim, C_DATA,  r'$x_0$', radius=0.28, fontsize=9)

# Sub-sampled steps (smaller)
sub = [2, 5]
radius_sub = 0.20
for s in sub:
    draw_circle(ax_ddim, x_pos[s], y_ddim, C_DDIM, f'$x_{{{s}}}$', radius=radius_sub, fontsize=7)

# Sequential arrows among sub-sampled
draw_arrow(ax_ddim, x_pos[-1]+0.00, y_ddim+0.00, x_pos[sub[0]]-radius_sub, y_ddim, C_DDIM, lw=1.3)
for i in range(len(sub)-1):
    draw_arrow(ax_ddim, x_pos[sub[i]]+radius_sub, y_ddim, x_pos[sub[i+1]]-radius_sub, y_ddim, C_DDIM, lw=1.3)
draw_arrow(ax_ddim, x_pos[sub[-1]]+radius_sub, y_ddim, x_pos[0]-0.28, y_ddim, C_DDIM, lw=1.3)

# Direct jump (T → 0) – the hallmark of DDIM
ax_ddim.annotate('', xy=(x_pos[0]+0.28, y_ddim), xytext=(x_pos[-1]-0.28, y_ddim),
                 arrowprops=dict(arrowstyle='->', color=C_DDIM, lw=2.5,
                                 connectionstyle='arc3,rad=-0.30',
                                 linestyle='dashed'),
                 zorder=4)
ax_ddim.text((x_pos[0]+x_pos[-1])/2+0.3, y_ddim+0.55, 'skip-step\n(direct T → 0)',
             fontsize=7, color=C_DDIM, ha='center', va='bottom', alpha=0.85,
             bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=C_DDIM, alpha=0.7))

# Deterministic label
ax_ddim.text(x_pos[-1], y_ddim-0.65, 'Deterministic\n(no noise injection)',
             fontsize=7, color=C_DDIM, ha='center', va='top', alpha=0.8,
             bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=C_DDIM, alpha=0.6))

# Non-Markovian forward process note
ax_ddim.text(x_pos[4]+0.1, y_ddim+0.57, r'$q_\sigma(x_t|x_0)$', fontsize=8,
             color=C_DDIM, ha='center', style='italic', alpha=0.7)

ax_ddim.set_xlim(-0.5, N+0.3)
ax_ddim.set_ylim(-0.7, 1.5)
ax_ddim.set_aspect('equal')
ax_ddim.axis('off')
ax_ddim.set_title('(c) DDIM: non-Markovian, deterministic, skip-step', loc='left',
                  fontsize=11, fontweight='bold', pad=6)

# ============================================================
# (d) Latent trajectory comparison
# ============================================================
ax_traj.set_xlim(-0.05, 1.05)
ax_traj.set_ylim(-0.05, 1.05)

# Latent space background
bg = plt.Circle((0.5, 0.5), 0.50, color='#f5f5f5', alpha=0.4,
                ec='#cccccc', linewidth=1.0, linestyle='--', zorder=1)
ax_traj.add_patch(bg)
ax_traj.text(0.5, 0.97, 'Latent Space', fontsize=9, color='#999999',
             ha='center', va='center', style='italic')

# x_T noise region
nr = plt.Circle((0.08, 0.90), 0.18, color=C_NOISE, alpha=0.10,
                ec=C_NOISE, linewidth=1.2, linestyle='--', zorder=2)
ax_traj.add_patch(nr)
ax_traj.text(0.08, 0.90, r'$x_T$', fontsize=10, fontweight='bold', color=C_NOISE,
             ha='center', va='center', zorder=8)

# x_0 data region
dr = plt.Circle((0.92, 0.08), 0.18, color=C_DATA, alpha=0.10,
                ec=C_DATA, linewidth=1.2, linestyle='--', zorder=2)
ax_traj.add_patch(dr)
ax_traj.text(0.92, 0.08, r'$x_0$', fontsize=10, fontweight='bold', color=C_DATA,
             ha='center', va='center', zorder=8)

# DDPM trajectory (wiggly, stochastic)
np.random.seed(42)
ddpm_xy = [(0.12, 0.86), (0.22, 0.76), (0.34, 0.70), (0.46, 0.58),
           (0.52, 0.46), (0.68, 0.32), (0.80, 0.20), (0.88, 0.12)]
for i in range(len(ddpm_xy)-1):
    ax_traj.plot([ddpm_xy[i][0], ddpm_xy[i+1][0]],
                 [ddpm_xy[i][1], ddpm_xy[i+1][1]],
                 color=C_DDPM, lw=2.0, alpha=0.65, zorder=5)
    ax_traj.scatter(ddpm_xy[i][0], ddpm_xy[i][1], color=C_DDPM, s=25,
                    alpha=0.65, zorder=6, edgecolors='white', linewidth=0.5)
ax_traj.scatter(ddpm_xy[-1][0], ddpm_xy[-1][1], color=C_DDPM, s=25,
                alpha=0.65, zorder=6, edgecolors='white', linewidth=0.5)

# DDIM trajectory (straight, deterministic)
ddim_xy = [(0.10, 0.88), (0.28, 0.70), (0.50, 0.48), (0.72, 0.26), (0.90, 0.10)]
for i in range(len(ddim_xy)-1):
    ax_traj.plot([ddim_xy[i][0], ddim_xy[i+1][0]],
                 [ddim_xy[i][1], ddim_xy[i+1][1]],
                 color=C_DDIM, lw=2.5, alpha=0.75, zorder=5)
    ax_traj.scatter(ddim_xy[i][0], ddim_xy[i][1], color=C_DDIM, s=35,
                    alpha=0.8, zorder=6, edgecolors='white', linewidth=0.5, marker='s')
ax_traj.scatter(ddim_xy[-1][0], ddim_xy[-1][1], color=C_DDIM, s=35,
                alpha=0.8, zorder=6, edgecolors='white', linewidth=0.5, marker='s')

# DDIM direct jump (dashed arc)
ax_traj.annotate('', xy=(0.50, 0.48), xytext=(0.10, 0.88),
                 arrowprops=dict(arrowstyle='->', color=C_DDIM, lw=1.2,
                                 connectionstyle='arc3,rad=-0.20',
                                 linestyle='dashed', alpha=0.35),
                 zorder=3)

# Legend
legend = ax_traj.legend(
    handles=[
        mpatches.Patch(color=C_DDPM, label='DDPM (step-by-step, stochastic)', alpha=0.8),
        mpatches.Patch(color=C_DDIM, label='DDIM (fewer steps, deterministic)', alpha=0.8),
        plt.Line2D([0], [0], color=C_DDIM, lw=1.2, linestyle='dashed', alpha=0.4,
                   label='DDIM direct jump'),
    ],
    loc='lower right', fontsize=7.5, framealpha=0.85,
    edgecolor='#cccccc', ncol=1
)
ax_traj.add_artist(legend)

# Annotation on trajectory
ax_traj.text(0.42, 0.68, 'Fewer steps → faster sampling', fontsize=7.5,
             color=C_DDIM, ha='center', va='bottom', alpha=0.7, rotation=-38)

ax_traj.set_aspect('equal')
ax_traj.axis('off')
ax_traj.set_title('(d) Latent trajectory comparison', loc='left',
                  fontsize=11, fontweight='bold', pad=6)

# ============================================================
# Save both PNG (300dpi) and PDF
# ============================================================
plt.savefig('/home/ubuntu/pythonProject1/ddim_concept_diagram.png', dpi=300,
            bbox_inches='tight', pad_inches=0.05)
plt.savefig('/home/ubuntu/pythonProject1/ddim_concept_diagram.pdf',
            bbox_inches='tight', pad_inches=0.05)
plt.close()
print("✅ Done! ddim_concept_diagram.png + .pdf (7.5×8.5 in, 300dpi)")
