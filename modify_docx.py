"""
Modify the thesis document content based on teacher comments.
Only changes content (not formatting) and updates TOC.
"""
import zipfile
from lxml import etree

DOCX_PATH = '张延开毕业论文(1).docx'
OUTPUT_PATH = '张延开毕业论文(1)_modified.docx'

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def get_p_text(p):
    texts = []
    for t in p.findall('.//w:t', ns):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)

def set_p_text(p, new_text):
    t_elements = p.findall('.//w:t', ns)
    if not t_elements:
        return
    t_elements[0].text = new_text
    for t in t_elements[1:]:
        parent = t.getparent()
        if parent is not None:
            parent.remove(t)

def find_text(paras, frag, start=0):
    for i in range(start, len(paras)):
        if frag in get_p_text(paras[i]):
            return i
    return -1

def is_heading(p):
    ppr = p.find('.//w:pStyle', ns)
    if ppr is not None:
        val = ppr.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '')
        if val.isdigit():
            return True
    return False

# Read original document
with zipfile.ZipFile(DOCX_PATH, 'r') as z:
    doc_xml = z.read('word/document.xml')
    files = {name: z.read(name) for name in z.namelist()}

tree = etree.fromstring(doc_xml)
body = tree.find('.//w:body', ns)
paras = body.findall('.//w:p', ns)
mods = []

# ======== 1. Chinese abstract: Add full names for DDIM and RS (Comment 1) ========
idx = find_text(paras, '[摘 要]')
if idx >= 0:
    old = get_p_text(paras[idx])
    new = old.replace('DDIM确定性可逆采样',
               '去噪扩散隐式模型（Denoising Diffusion Implicit Models, DDIM）确定性可逆采样', 1)
    new = new.replace('Reed-Solomon 纠错编码', 'Reed-Solomon（RS）纠错编码', 1)
    if new != old:
        set_p_text(paras[idx], new)
        mods.append("1. Chinese abstract: Added full names for DDIM and RS")

# ======== 2. English abstract: Rewrite to match Chinese (Comments 2/3) ========
idx = find_text(paras, 'Abstract：')
if idx >= 0:
    en = (
        'Abstract: Aiming at the problem that existing coverless image steganography methods '
        'based on diffusion models mostly focus on image-to-image hiding within the same modality '
        'and suffer from limited key diversity, this paper proposes a cross-modal coverless '
        'steganography method integrating a multi-modal private key. The method leverages the '
        'DDIM deterministic reversible sampling of a pre-trained diffusion model as the core '
        'mechanism, extending the secret information from images to text labels with limited '
        'semantic categories. The secret text is first encoded via Reed-Solomon error-correcting '
        'code, then embedded into the initial latent noise by assigning strong positive/negative '
        'signals at positions jointly determined by the hash of a private image and a fixed '
        'private text. The container image is generated through DDIM deterministic sampling guided '
        'by a public text prompt. The receiver recovers the noise via DDIM inversion, reads the '
        'symbols at the same positions, and decodes the original secret text via RS decoding. '
        'The private key adopts a multi-modal design (image + fixed text), while the public key '
        'is a text prompt controlling the visual content. Experiments on 1,000 instances with '
        'different public prompts show 100% extraction success rate under both no-attack and '
        'JPEG compression (quality 30–70) conditions, demonstrating the robustness of the method.'
    )
    set_p_text(paras[idx], en)
    mods.append("2. English abstract: Rewritten to match Chinese abstract content")

# ======== 3. 研究目的: Add research background (Comment 12) ========
idx = find_text(paras, '研究目的', 80)
if idx >= 0 and idx + 1 < len(paras):
    new_text = (
        '无载体图像隐写是信息隐藏领域的重要研究方向，其核心思想是直接生成含密图像而非修改现有载体，'
        '从而从根源上消除隐写分析检测的依据。近年来，扩散模型在图像生成任务中展现出卓越性能，'
        '其采样过程的天然可逆性为构建新一代无载体隐写方案提供了独特的技术优势。'
        '然而，现有基于扩散模型的隐写方法仍多集中于图像到图像的同模态隐藏，且密钥形式单一，'
        '在实际应用中存在模态适配性不足和安全性受限的问题。'
        '本课题以扩散模型的DDIM确定性可逆采样为核心技术路线，旨在设计一种融合多模态密钥的'
        '跨模态无载体隐写方法，将秘密信息类型从图像拓展至文本语义类别，'
        '并探索多模态私钥机制对隐藏过程安全性的提升作用。'
    )
    set_p_text(paras[idx + 1], new_text)
    mods.append("3. 研究目的: Rewritten to include research background context")

# ======== 4. 研究意义: Remove AI flavor (Comment 14) ========
idx = find_text(paras, '理论意义', 80)
if idx >= 0:
    set_p_text(paras[idx],
        '理论意义在于探索扩散模型在跨模态隐写任务中的适用性，分析潜空间信号调制对信息隐藏'
        '可靠性的影响规律，为无载体隐写的跨模态扩展提供技术参考。'
        '应用价值方面，该方法无需训练、部署成本低，适用于隐蔽通信和数字版权保护等场景。')
    mods.append("4. 研究意义: Removed AI-flavored writing")

# ======== 5. 传统隐写方法: Reduce AI flavor (Comment 16) ========
idx = find_text(paras, '传统隐写方法及其局限', 80)
if idx >= 0:
    set_p_text(paras[idx],
        '传统隐写方法大致分为空间域和变换域两类：空间域方法通过修改像素的最低有效位（LSB）'
        '或利用像素值差异（PVD）嵌入信息[1]，变换域方法则在DCT、DWT等频域系数上进行修改[2]。'
        '这类方法虽实现简单，但会在载体中引入统计异常。随着深度学习隐写分析技术（如XuNet、'
        'YedroudjNet等）的发展[3]，此类方法的检测风险日益增加。自适应隐写策略（如S-UNIWARD）[4]'
        '通过设计失真函数将修改集中在纹理复杂区域以提升抗检测能力，但本质上仍依赖对载体的物理修改。')
    mods.append("5. 传统隐写方法: Rewritten to reduce AI flavor")

# ======== 6. Citation format fix (Comment 18) ========
idx = find_text(paras, '取自CRoSS', 80)
if idx >= 0:
    set_p_text(paras[idx],
        '根据上述定义，可将隐藏过程视为秘密图像与容器图像之间的转换，'
        '而提取过程则是隐藏过程的逆过程。该定义框架参考了CRoSS方法[1]中的任务形式化描述。')
    mods.append("6. Citation: Fixed format (taken from CRoSS -> proper citation)")

# ======== 7. 研究目标: Differentiate from 研究目的 (Comment 24) ========
idx = find_text(paras, '总体目标', 80)
if idx >= 0:
    set_p_text(paras[idx],
        '本研究的总体目标为：设计并实现一种融合多模态密钥的跨模态无载体隐写方法，'
        '将秘密信息类型从图像拓展至文本语义类别，在保证生成图像质量的前提下，'
        '实现文本信息在图像中的可靠隐藏与恢复。')
    mods.append("7. 研究目标: Rewritten to differentiate from 研究目的")

idx = find_text(paras, '第三，', 105)
if idx >= 0:
    set_p_text(paras[idx],
        '第三，在有限计算资源下完成方法的可行性验证。以单块消费级GPU为主要计算平台，'
        '从提取成功率、抗攻击鲁棒性及参数影响分析三个维度系统评估方法性能，'
        '验证轻量级跨模态隐写在资源受限场景下的可行性。')
    mods.append("8. 研究目标-第三子目标: Removed LSB overlap with 研究内容")

# ======== 8. 研究内容: Condense (Comment 27) ========
idx_h = find_text(paras, '研究内容', 105)
if idx_h >= 0:
    # Find where the next heading after 研究内容 starts
    section_end = len(paras)
    for pi in range(idx_h + 2, min(idx_h + 30, len(paras))):
        if is_heading(paras[pi]):
            section_end = pi
            break

    # Condensed content to replace the verbose section
    condensed = [
        '本研究的具体内容分为以下三个部分：',
        '（一）无载体隐写技术现状分析与问题归纳。对现有基于扩散模型的无载体隐写方法进行系统梳理，'
        '重点分析CRoSS等核心框架的基本原理与实现路径，总结现有方法在秘密信息类型、'
        '密钥形式和抗攻击能力等方面的特点与不足。',
        '（二）基于多模态密钥的跨模态隐写方法设计。提出一种融合多模态密钥的跨模态无载体隐写框架，'
        '包括跨模态信息编码与解码机制、多模态密钥融合策略和可逆隐藏与提取流程三个方面。',
        '（三）实验验证与性能评估。通过实验对所提方法进行系统验证，评估在无攻击和多种退化条件下的'
        '提取成功率，分析关键参数对性能的影响。',
    ]

    # Replace first N paragraphs with condensed versions
    start = idx_h + 1
    for i, text in enumerate(condensed):
        pi = start + i
        if pi < section_end:
            set_p_text(paras[pi], text)

    # Clear remaining content paragraphs in this section
    clear_start = start + len(condensed)
    # BUT only clear up to section_end, NOT to end of document!
    for pi in range(clear_start, section_end):
        set_p_text(paras[pi], '')

    mods.append(f"9. 研究内容: Condensed (section range: {start}-{section_end})")

# ======== 9. Remove orphan table reference (Comment 38) ========
idx = find_text(paras, '表 1.2.4-1')
if idx >= 0:
    # Check if this is an exact match for a table label vs a reference in text
    text = get_p_text(paras[idx]).strip()
    if text == '表 1.2.4-1':
        set_p_text(paras[idx], '本文方法涉及的参数及其取值将在后续章节详细说明。')
        mods.append("10. Removed orphan table header (表1.2.4-1)")

# ======== 10. 预备知识: Log only (Comment 40) ========
idx = find_text(paras, '预备知识', 160)
if idx >= 0:
    mods.append("11. 预备知识: Content kept (structural change requires chapter reorganization)")

# ======== 11. Fix AI-flavored sampling parameters (Comment 65) ========
idx = find_text(paras, '采样参数：DDIM', 300)
if idx >= 0:
    set_p_text(paras[idx], 'DDIM采样步数设为50，引导尺度为7.5，采用确定性模式（η=0）。')
    mods.append("12. Sampling parameters: Reduced AI flavor")

# ======== 12. Fix AI-flavored private key description (Comment 68) ========
idx = find_text(paras, '私钥图像：private_cat.jpg', 350)
if idx >= 0:
    set_p_text(paras[idx], '私钥图像固定为private_cat.jpg（512×512彩色图像），私钥文本固定为"mykey"。')
    mods.append("13. Private key description: Reduced AI flavor")

# ======== 13. Add in-text figure/table references (Comment 73) ========
# Only add references to paragraphs that don't already reference the figure/table
figure_map = {
    '图 3.3-1': ('JPEG', '对应的实验结果如图3.3-1所示。'),
    '图 3.3-2': ('高斯噪声', '对应的实验结果如图3.3-2所示。'),
    '图 3.3-3': ('裁剪', '对应的实验结果如图3.3-3所示。'),
    '图 3.3-4': ('参数', '对应的参数影响分析如图3.3-4所示。'),
    '图 3.4-1': ('对比', '对比实验结果如图3.4-1所示。'),
}

for fig_name, (keyword, ref_text) in figure_map.items():
    for pi in range(350, len(paras)):
        if get_p_text(paras[pi]).strip() == fig_name:
            if pi > 0:
                prev = get_p_text(paras[pi - 1])
                if '图' not in prev and keyword in prev:
                    new_prev = prev.rstrip('。') + '，' + ref_text
                    set_p_text(paras[pi - 1], new_prev)
                    mods.append(f"14. {fig_name}: Added in-text reference")
            break

# Table 3.1.2-1 already has in-text reference in paragraph 312, no change needed
mods.append("15. Table 3.1.2-1: Already has in-text reference")

# ======== 14. Improve LSB comparison discussion (Comment 78) ========
idx = find_text(paras, '为了进一步验证本方法的优越性', 380)
if idx >= 0:
    set_p_text(paras[idx],
        '为进一步评估本文方法的性能水平，将其与LSB隐写方法进行了对比实验。'
        'LSB是一种经典的空间域隐写方法，虽然与本文方法在技术路径上存在本质差异'
        '（前者属于载体修改式隐写，后者属于生成式无载体隐写），'
        '将其作为基准参照有助于从提取成功率角度直观展示生成式隐写相对于传统修改式隐写'
        '在抗退化能力方面的差异。LSB方法将秘密比特写入图像像素的RGB三通道最低位，'
        '每个像素可隐藏3比特信息。对比实验在无攻击、JPEG压缩（质量70/50/30）和'
        '高斯噪声（sigma=10）五种条件下进行。')
    mods.append("16. Comparison experiment: Added context about LSB comparison rationale")

# ======== Save ========
# Update settings.xml to auto-update fields (TOC) on open
ns_w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
if 'word/settings.xml' in files:
    settings_tree = etree.fromstring(files['word/settings.xml'])
    update = settings_tree.find(f'{{{ns_w}}}updateFields')
    if update is None:
        update = etree.SubElement(settings_tree, f'{{{ns_w}}}updateFields')
    update.set(f'{{{ns_w}}}val', 'true')
    files['word/settings.xml'] = etree.tostring(settings_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

modified_doc_xml = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)

with zipfile.ZipFile(OUTPUT_PATH, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in files.items():
        if name == 'word/document.xml':
            zout.writestr(name, modified_doc_xml)
        else:
            zout.writestr(name, data)

print("=== Modifications Applied ===")
for m in mods:
    print(m)
print(f"\nOutput saved to: {OUTPUT_PATH}")
