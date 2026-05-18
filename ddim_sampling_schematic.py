import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ================================================================
# 1. Generate a clean cat face image
# ================================================================
def make_cat_image(S=140):
    """Create a cat face using geometric primitives on a grid."""
    x = np.linspace(-1, 1, S)
    y = np.linspace(-1, 1, S)
    X, Y = np.meshgrid(x, y)
    img = np.ones((S, S, 3), dtype=np.float64) * 0.97

    def fill(mask, color):
        for c in range(3):
            img[:,:,c] = np.where(mask, color[c], img[:,:,c])

    FUR   = np.array([0.22, 0.22, 0.22])
    INNER = np.array([0.82, 0.54, 0.60])
    WHITE = np.array([0.94, 0.94, 0.94])
    BLACK = np.array([0.06, 0.06, 0.06])
    NOSE  = np.array([0.78, 0.48, 0.52])

    # Head
    fill((X**2 + (Y - 0.05)**2 * 1.3) < 0.74**2, FUR)

    # Ears (extend beyond head)
    fill((((X + 0.34)**2 + (Y - 0.20)**2) < 0.30**2) & (Y < 0.02) & ~((X**2 + (Y - 0.05)**2 * 1.3) < 0.74**2), FUR)
    fill((((X - 0.34)**2 + (Y - 0.20)**2) < 0.30**2) & (Y < 0.02) & ~((X**2 + (Y - 0.05)**2 * 1.3) < 0.74**2), FUR)

    # Inner ears
    fill((((X + 0.34)**2 + (Y - 0.20)**2) < 0.17**2) & (Y < 0.0), INNER)
    fill((((X - 0.34)**2 + (Y - 0.20)**2) < 0.17**2) & (Y < 0.0), INNER)

    # Eyes
    fill(((X + 0.18)**2 + Y**2) < 0.09**2, WHITE)
    fill(((X - 0.18)**2 + Y**2) < 0.09**2, WHITE)
    # Pupils
    fill(((X + 0.16)**2 + (Y + 0.01)**2) < 0.040**2, BLACK)
    fill(((X - 0.16)**2 + (Y + 0.01)**2) < 0.040**2, BLACK)

    # Nose
    fill((np.abs(X) < 0.050) & (Y > 0.04) & (Y < 0.10), NOSE)

    # Mouth
    fill(((X + 0.045)**2 + (Y - 0.10)**2 < 0.040**2) & (X < 0), BLACK * 0.5)
    fill(((X - 0.045)**2 + (Y - 0.10)**2 < 0.040**2) & (X > 0), BLACK * 0.5)

    # Whiskers
    for dx, dy, a, b, ang in [
        (-0.35, 0.0, 0.18, 0.014, -5), (-0.37, 0.06, 0.18, 0.014, 3),
        (-0.35, -0.06, 0.18, 0.014, -12), (0.35, 0.0, 0.18, 0.014, 5),
        (0.37, 0.06, 0.18, 0.014, -3), (0.35, -0.06, 0.18, 0.014, 12),
    ]:
        ang_r = np.deg2rad(ang)
        xr = (X - dx) * np.cos(ang_r) - (Y - dy) * np.sin(ang_r)
        yr = (X - dx) * np.sin(ang_r) + (Y - dy) * np.cos(ang_r)
        fill(((xr / a)**2 + (yr / b)**2) < 1.0, FUR * 0.7)

    # Simple blur
    k = 3
    k1 = np.exp(-np.arange(-k//2+1, k//2+1)**2 / (2*0.6**2))
    k1 /= k1.sum()
    for c in range(3):
        tmp = img[:,:,c].copy()
        for _ in range(2):
            tmp = np.apply_along_axis(lambda v: np.convolve(v, k1, mode='same'), 0, tmp)
        img[:,:,c] = tmp
    return np.clip(img, 0, 1).astype(np.float32)


# ================================================================
# 2. DDIM denoising progression
# ================================================================
S = 140
x0 = make_cat_image(S)
rng = np.random.RandomState(2024)
noise = rng.randn(S, S, 3).astype(np.float32)
noise = noise / np.sqrt((noise**2).mean())

alphas = [0.00, 0.08, 0.25, 0.55, 0.88, 1.00]
t_labels = [r'$x_T$', r'$x_{t_4}$', r'$x_{t_3}$', r'$x_{t_2}$', r'$x_{t_1}$', r'$x_0$']

images = []
for a in alphas:
    noisy = np.sqrt(a) * x0 + np.sqrt(max(1 - a, 0)) * noise
    images.append(np.clip(noisy, 0, 1))


# ================================================================
# 3. Build figure — clean figure-fraction coordinates
# ================================================================
W, H = 12.8, 7.2  # 16:9
fig = plt.figure(figsize=(W, H))
fig.patch.set_facecolor('white')

N = len(images)
img_w = 0.115      # image width in figure fraction
img_h = img_w * W / H  # square panel (~0.204)
gap = 0.045        # gap between images
total_w = N * img_w + (N - 1) * gap
margin = (1 - total_w) / 2

img_y = 0.56       # bottom of image row
arrow_y = img_y + img_h / 2  # vertical center of images

img_lefts = [margin + i * (img_w + gap) for i in range(N)]

# ---- Plot each image ----
for i in range(N):
    ax = fig.add_axes([img_lefts[i], img_y, img_w, img_h])
    ax.imshow(images[i], interpolation='bicubic', aspect='auto')
    ax.axis('off')
    ax.set_title(t_labels[i], fontsize=11, fontweight='bold', pad=6, color='#222222')

# ---- Arrows between images ----
ax_arrows = fig.add_axes([0, 0, 1, 1], facecolor='none')
ax_arrows.set_xlim(0, 1)
ax_arrows.set_ylim(0, 1)
ax_arrows.axis('off')

for i in range(N - 1):
    x_s = img_lefts[i] + img_w + 0.003
    x_e = img_lefts[i + 1] - 0.003

    # Arrow
    ax_arrows.annotate('', xy=(x_e, arrow_y), xytext=(x_s, arrow_y),
                       arrowprops=dict(arrowstyle='->', color='#2166AC',
                                       lw=2.8, connectionstyle='arc3,rad=0.0'),
                       zorder=10)

    # Label
    cx = (x_s + x_e) / 2
    ax_arrows.text(cx, arrow_y + 0.24, 'deterministic step\n(reversible)',
                   fontsize=8, color='#2166AC', ha='center', va='bottom',
                   fontstyle='italic', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                             edgecolor='#2166AC', alpha=0.85))

# ---- Noise → structure gradient bar at top ----
ax_top = fig.add_axes([0, 0, 1, 1], facecolor='none')
ax_top.set_xlim(0, 1)
ax_top.set_ylim(0, 1)
ax_top.axis('off')

xL = img_lefts[0]
xR = img_lefts[-1] + img_w
y_bar = 0.93

ax_top.text(xL - 0.005, y_bar, 'noise dominates', fontsize=8.5, color='#B2182B',
            ha='right', va='center', alpha=0.75)
ax_top.text(xR + 0.005, y_bar, 'structure dominates', fontsize=8.5, color='#2166AC',
            ha='left', va='center', alpha=0.75)

# Gradient bar
for frac in np.linspace(0, 1, 300):
    xp = xL + frac * (xR - xL)
    c = (1 - frac) * np.array([0.698, 0.094, 0.169]) + frac * np.array([0.130, 0.400, 0.675])
    ax_top.plot([xp, xp], [y_bar - 0.020, y_bar + 0.020], color=c, lw=2.0, alpha=0.7,
                transform=ax_top.transData)

# ---- Bottom: formula box ----
ax_bot = fig.add_axes([0, 0, 1, 1], facecolor='none')
ax_bot.set_xlim(0, 1)
ax_bot.set_ylim(0, 1)
ax_bot.axis('off')

# Formula
formula = (r'$\mathbf{x}_{t-1} = \sqrt{\bar{\alpha}_{t-1}} \cdot '
           r'\hat{\mathbf{x}}_0(\mathbf{x}_t) + '
           r'\sqrt{1 - \bar{\alpha}_{t-1}} \cdot '
           r'\boldsymbol{\varepsilon}_\theta(\mathbf{x}_t)$')
ax_bot.text(0.5, 0.26, formula, fontsize=9.5, color='#222222',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.35', facecolor='#f8f8f8',
                      edgecolor='#cccccc', alpha=0.9))

# Explanation note
note = (r'DDIM defines a non-Markovian forward process '
        r'$q_\sigma(\mathbf{x}_t|\mathbf{x}_0)$ and trains with the same '
        r'$L_{\mathrm{simple}}$ as DDPM, but reverses deterministically, '
        r'enabling faster sampling without retraining.')
ax_bot.text(0.5, 0.14, note, fontsize=8, color='#444444',
            ha='center', va='center', style='italic')

# ---- Title ----
fig.suptitle('DDIM Deterministic Sampling Schematic',
             fontsize=17, fontweight='bold', color='#111111',
             x=0.015, y=0.97, ha='left', va='top')

# ================================================================
# Save
# ================================================================
plt.savefig('/home/ubuntu/pythonProject1/ddim_sampling_schematic.png',
            dpi=300, bbox_inches=None, pad_inches=0.1)
plt.savefig('/home/ubuntu/pythonProject1/ddim_sampling_schematic.pdf',
            bbox_inches=None, pad_inches=0.1)
plt.close()
print(f"Done! 16:9 diagram ({N} panels, {S}x{S} cat)")
