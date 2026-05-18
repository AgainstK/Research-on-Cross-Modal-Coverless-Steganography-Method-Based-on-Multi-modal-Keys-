import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'WenQuanYi Micro Hei'
matplotlib.rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import warnings; warnings.filterwarnings('ignore')

fig, ax = plt.subplots(1, 1, figsize=(28, 10))
ax.set_xlim(0, 28)
ax.set_ylim(0, 10)
ax.axis('off')

C  = {'b':'#E8F0FE','o':'#FFF3E0','g':'#E8F5E9','p':'#F3E5F5',
      'B':'#1565C0','O':'#E65100','G':'#2E7D32','P':'#6A1B9A'}

def box(ax, xy, w, h, text, c='b', bc='B', fs=10, bold=False):
    color, border = C.get(c,C['b']), C.get(bc,C['B'])
    p = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.1", facecolor=color,
                       edgecolor=border, linewidth=1.5, zorder=3)
    ax.add_patch(p)
    cx, cy = xy[0]+w/2, xy[1]+h/2
    lines = text.split('\n')
    n = len(lines)
    for i, ln in enumerate(lines):
        sz = max(fs-2, 7) if n>2 else fs
        ax.text(cx, cy+(n-1)*4.5-i*9, ln, ha='center', va='center',
                fontsize=sz, color='#222', fontweight='bold' if bold else 'normal')

def arr(ax, x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.55",
                                color='#888', lw=1.4), zorder=2)
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+0.15, label, ha='center', va='bottom',
                fontsize=7.5, color='#888')

# ===== TITLE =====
ax.text(14, 9.7, '实验加密与解密流程图', ha='center', fontsize=17,
        fontweight='bold', color='#0D47A1')

# =====================================================================
#  LEFT — ENCODING (horizontal flow, left to right)
# =====================================================================
ax.text(0.3, 9.0, '隐藏过程 (Encoding)', fontsize=13, fontweight='bold', color=C['B'])
ax.plot([0.3, 14.5], [8.7, 8.7], color='#CCC', lw=0.8)

# ── Row A: Secret text → RS → Bits ──
ya = 7.7
box(ax, (0.5,ya), 2.0,0.8, '秘密文本', 'b','B',11)
arr(ax, 2.5,ya+0.4, 3.8,ya+0.4)
box(ax, (3.8,ya), 2.0,0.8, 'RS编码', 'o','O',11)
arr(ax, 5.8,ya+0.4, 7.2,ya+0.4)
box(ax, (7.2,ya), 2.0,0.8, '秘密比特段', 'b','B',11)

# ── Row B: Key → SHA-256 → PRNG → Positions ──
yb = 6.3
box(ax, (0.5,yb), 2.0,0.8, '私钥+\n"mykey"', 'g','G',10)
arr(ax, 2.5,yb+0.4, 3.8,yb+0.4)
box(ax, (3.8,yb), 2.0,0.8, 'SHA-256\n→ PRNG', 'g','G',10)
arr(ax, 5.8,yb+0.4, 7.2,yb+0.4)
box(ax, (7.2,yb), 2.0,0.8, '240个\n嵌入位置', 'g','G',10)

# ── Row C: Prompt → CLIP → Embedding ──
yc = 4.9
box(ax, (0.5,yc), 2.0,0.8, '提示词\nPublic Prompt', 'p','P',10)
arr(ax, 2.5,yc+0.4, 3.8,yc+0.4)
box(ax, (3.8,yc), 2.0,0.8, 'CLIP\n文本编码', 'p','P',10)
arr(ax, 5.8,yc+0.4, 7.2,yc+0.4)
box(ax, (7.2,yc), 2.0,0.8, '文本嵌入', 'p','P',11)

# ── Row D: Seed → Init Latent ──
yd = 3.5
box(ax, (0.5,yd), 2.0,0.8, '随机种子\nseed=42', 'o','O',10)
arr(ax, 2.5,yd+0.4, 4.8,yd+0.4)
box(ax, (4.8,yd), 2.4,0.8, '初始潜变量\n(1×4×64×64)', 'b','B',10)

# CFG arrow
arr(ax, 9.2, yc+0.4, 7.2, yd+0.4, 'CFG=7.5')

# ── Three paths converge to MODULATION ──
arr(ax, 9.2, ya+0.4, 12.0, 5.6)
arr(ax, 9.2, yb+0.4, 12.0, 5.6)
arr(ax, 7.2, yd+0.4, 12.0, 5.6)

box(ax, (12.0, 4.9), 3.2, 1.4, '潜变量调制：\n240个元素\n按 ±δ 修改', 'o','O',11, bold=True)

# ── Stego Latent → DDIM → Output ──
arr(ax, 15.2, 5.6, 17.0, 5.6)
box(ax, (17.0, 5.2), 2.2, 0.8, '含密潜变量\nStego Latent', 'b','B',10)
arr(ax, 19.2, 5.6, 20.8, 5.6)
box(ax, (20.8, 4.8), 2.0, 1.6, 'DDIM去噪\n50步\nCFG=7.5', 'p','P',10)
arr(ax, 22.8, 5.6, 24.0, 5.6)
box(ax, (24.0, 5.2), 2.2, 0.8, '含密图像\n512×512', 'g','G',11)

# =====================================================================
#  RIGHT — DECODING (compact below the encoding)
# =====================================================================
ax.text(0.3, 2.6, '提取过程 (Decoding)', fontsize=13, fontweight='bold', color=C['B'])
ax.plot([0.3, 27.5], [2.3, 2.3], color='#CCC', lw=0.8)

# Simplified decode flow
bx = 0.5
by = 1.3

# Stego image path (top layer)
box(ax, (bx, by+0.3), 1.8,0.7, '含密图像', 'g','G',10)
arr(ax, 2.3, by+0.65, 3.5, by+0.65)
box(ax, (3.5, by+0.3), 1.6,0.7, 'VAE', 'b','B',10)
arr(ax, 5.1, by+0.65, 6.3, by+0.65)
box(ax, (6.3, by+0.3), 1.6,0.7, '含密\n潜变量', 'b','B',9)

# Reference image path (bottom layer)
box(ax, (bx, by-0.8), 1.8,0.7, '参考图像\n(同种子提示词)', 'p','P',8)
arr(ax, 2.3, by-0.45, 3.5, by-0.45)
box(ax, (3.5, by-0.8), 1.6,0.7, 'VAE', 'p','P',10)
arr(ax, 5.1, by-0.45, 6.3, by-0.45)
box(ax, (6.3, by-0.8), 1.6,0.7, '参考\n潜变量', 'p','P',9)

# Merge → Compare → RS → Text
arr(ax, 7.9, by+0.65, 9.5, by+0.65)
arr(ax, 7.9, by-0.45, 9.5, by+0.65)
box(ax, (9.5, by+0.3), 2.2,0.7, '差值比较\n提取比特', 'o','O',10)
arr(ax, 11.7, by+0.65, 13.3, by+0.65)
box(ax, (13.3, by+0.3), 1.6,0.7, 'RS解码', 'o','O',10)
arr(ax, 14.9, by+0.65, 16.3, by+0.65)
box(ax, (16.3, by+0.3), 1.8,0.7, '秘密文本', 'g','G',10)

# Method label
ax.plot([0.05,0.05], [by-1.1, by+0.8], color='#AAA', lw=1)
ax.text(-0.05, by-0.15, '参考\n比较法', ha='center', fontsize=8, color='#999')

# ===== SAVE =====
outdir = '/home/ubuntu/pythonProject1/RESULT/fine_experiments'
plt.savefig(f'{outdir}/encryption_flowchart.png', dpi=200,
            bbox_inches='tight', facecolor='white', pad_inches=0.4)
plt.savefig(f'{outdir}/encryption_flowchart.pdf',
            bbox_inches='tight', facecolor='white', pad_inches=0.4)
print("Saved encryption_flowchart.png + .pdf")
