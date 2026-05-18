"""Encryption flow diagram v6 — PIL-based, pixel-perfect."""
from PIL import Image, ImageDraw, ImageFont
import os

FONT_FILE = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
OUT_DIR = "/home/ubuntu/pythonProject1/RESULT/fine_experiments"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 3200, 1050
WHITE = (255, 255, 255, 255)
GRAY = (160, 160, 160)
DARK = (50, 50, 50)

# Color schemes
BLUE   = {'bg': (227, 242, 253), 'ec': (21, 101, 192)}
ORANGE = {'bg': (255, 243, 224), 'ec': (230, 81, 0)}
PURPLE = {'bg': (243, 229, 245), 'ec': (106, 27, 154)}
GREEN  = {'bg': (232, 245, 233), 'ec': (46, 125, 50)}

img = Image.new('RGBA', (W, H), WHITE)
draw = ImageDraw.Draw(img)

# Fonts
def getfnt(size):
    try: return ImageFont.truetype(FONT_FILE, size)
    except: return ImageFont.load_default()

ft_title = getfnt(36)
ft_main  = getfnt(28)
ft_sub   = getfnt(22)
ft_tiny  = getfnt(17)

def rbox(x, y, w, h, r, fill, outline, lw=3):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=r, fill=fill, outline=outline, width=lw)

def ctext(cx, cy, text, font, fill=DARK):
    b = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (b[2]-b[0])//2, cy - (b[3]-b[1])//2), text, font=font, fill=fill)

def dbox(x, y, w, h, lines, scheme, font, r=14):
    rbox(x, y, w, h, r, scheme['bg'], scheme['ec'], 4)
    cx, cy = x+w//2, y+h//2
    n = len(lines)
    gap = 38
    start = cy - (n-1)*gap//2
    for i, ln in enumerate(lines):
        ctext(cx, start + i*gap, ln, font)

def arrow(x1, y1, x2, y2):
    draw.line([(x1, y1), (x2, y2)], fill=GRAY, width=4)
    dx, dy = x2-x1, y2-y1
    L = (dx*dx + dy*dy)**0.5
    if L < 1: return
    ux, uy = dx/L, dy/L
    hl, hw_ = 18, 8
    tip = (x2, y2)
    base = (x2 - ux*hl, y2 - uy*hl)
    draw.polygon([tip, (base[0]-uy*hw_, base[1]+ux*hw_), (base[0]+uy*hw_, base[1]-ux*hw_)], fill=GRAY)

# ── Title ──
ctext(W//2, 38, '加密流程', ft_title, fill=(13, 71, 161))

# ── Main 5-box pipeline ──
my = 100
bh = 240
gap = 50
bw = (W - 2*80 - 4*gap) // 5  # ~542
bx = [80 + i*(bw+gap) for i in range(5)]
labels = [
    ['秘密文本', 'Secret'],
    ['RS编码', '(10,20)'],
    ['潜空间调制', '240×±δ'],
    ['DDIM去噪', '50步,CFG=7.5'],
    ['含密图像', '512×512'],
]
schemes = [BLUE, ORANGE, ORANGE, PURPLE, GREEN]

for i in range(5):
    dbox(bx[i], my, bw, bh, labels[i], schemes[i], ft_main)
for i in range(4):
    arrow(bx[i]+bw, my+bh//2, bx[i+1], my+bh//2)

# ── Private key path (below) ──
py = my + bh + 30
# Private key box (left)
pk_w, pk_h = 380, 160
dbox(80, py, pk_w, pk_h, ['私钥图像+mykey', 'SHA-256→PRNG'], GREEN, ft_sub)
# Arrow from private key to position box
arrow(80 + pk_w//2, py + pk_h, 80 + pk_w//2, py + pk_h + 30)
# "240个位置" box
pos_w, pos_h = 300, 70
pos_x = 80 + pk_w//2 - pos_w//2
dbox(pos_x, py + pk_h + 30, pos_w, pos_h, ['240个位置'], GREEN, ft_sub)
# Arrow from position box to main pipeline (box 3)
arrow(pos_x + pos_w//2, py + pk_h + 30, bx[2], my + bh//2)
ctext(pos_x + pos_w//2 + 60, py + pk_h + 30 - 25, '位置索引', ft_tiny, fill=GREEN['ec'])

# ── Prompt path (below) ──
pr_y = py + pk_h + 130
pr_w, pr_h = 340, 55
dbox(80, pr_y, pr_w, pr_h, ['提示词→CLIP编码'], PURPLE, ft_tiny)
# Arrow → right, stopping under box 5
arrow(80 + pr_w, pr_y + pr_h//2, bx[4] + bw, pr_y + pr_h//2)
ctext(W//2, pr_y - 2, '文本嵌入 + CFG引导', ft_tiny, fill=PURPLE['ec'])

# ── Seed path (above) ──
sd_w, sd_h = 520, 70
dbox(bx[2], 10, sd_w, sd_h, ['种子42 → 初始潜变量 (1×4×64×64)'], ORANGE, ft_tiny)
arrow(bx[2] + sd_w//2, 10 + sd_h, bx[2] + sd_w//2, my)

# Save
out_png = f'{OUT_DIR}/encryption_flow_v2.png'
img.save(out_png)
print(f'Saved: {out_png} ({W}x{H})')
img.close()
