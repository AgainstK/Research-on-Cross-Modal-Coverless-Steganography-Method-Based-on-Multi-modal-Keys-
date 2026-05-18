#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模鲁棒性实验脚本：参数敏感性、ECC长度、文本多样性、攻击鲁棒性、LSB对比
"""

import os, sys, io, csv, random, time, json
import numpy as np
import torch
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

sys.path.insert(0, '.')
from stego_working import (
    load_pipe, hide, reveal, _reveal_by_reference,
    _generate_clean_reference, _vae_encode, _clean_ref_cache,
    text_to_bits, bits_to_text, get_indices,
    MSG_LEN, ECC_LEN, get_rs
)

PRIVATE_IMAGE = "private_cat.jpg"
RESULT_DIR = "RESULT/experiments"
os.makedirs(RESULT_DIR, exist_ok=True)

# ========== 工具函数 ==========

def jpeg_compress(img, quality):
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality)
    buf.seek(0)
    return Image.open(buf).convert('RGB')

def add_gaussian_noise(img, sigma):
    img_np = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, sigma, img_np.shape)
    return Image.fromarray(np.clip(img_np + noise, 0, 255).astype(np.uint8))

def random_crop(img, min_scale=0.7, target_size=(512, 512)):
    w, h = img.size
    scale = random.uniform(min_scale, 1.0)
    nw, nh = int(w * scale), int(h * scale)
    left = random.randint(0, w - nw) if w > nw else 0
    top = random.randint(0, h - nh) if h > nh else 0
    return img.crop((left, top, left + nw, top + nh)).resize(target_size, Image.LANCZOS)

def extract_safe(test_img, private_path, prompt, msg_len=MSG_LEN, ecc_len=ECC_LEN):
    """Safe extraction that returns (secret, success)"""
    try:
        result = _reveal_by_reference(test_img, private_path, prompt,
                                      msg_len=msg_len, ecc_len=ecc_len)
        return result, True
    except Exception:
        return None, False

def clear_cache():
    _clean_ref_cache.clear()

# ========== 实验1: 参数敏感性 ==========

def experiment1_delta_sensitivity():
    print("\n" + "="*60)
    print("实验1: 嵌入强度 δ 参数敏感性")
    print("="*60)

    secret = "cat"
    prompt = "A majestic mountain landscape"
    deltas = [1.0, 1.5, 2.0, 2.5, 3.0]
    n_images = 50

    results = {}
    for delta in deltas:
        clear_cache()
        subdir = os.path.join(RESULT_DIR, f"exp1_delta_{delta:.1f}")
        os.makedirs(subdir, exist_ok=True)
        success = 0

        for i in range(n_images):
            out_path = os.path.join(subdir, f"img_{i:04d}.png")
            hide(secret, PRIVATE_IMAGE, prompt, out_path, delta=delta)

            img = Image.open(out_path).convert("RGB")
            result, ok = extract_safe(img, PRIVATE_IMAGE, prompt)
            if ok and result == secret:
                success += 1

        rate = success / n_images * 100
        results[delta] = rate
        print(f"  δ={delta:.1f}: {success}/{n_images} ({rate:.1f}%)")

    # Save CSV
    csv_path = os.path.join(RESULT_DIR, "exp1_delta_sensitivity.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["delta", "success", "total", "rate"])
        for d, r in results.items():
            writer.writerow([d, int(r * n_images / 100), n_images, r])

    # Plot
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(list(results.keys()), list(results.values()), 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('Embedding Strength δ', fontsize=12)
    ax.set_ylabel('Extraction Success Rate (%)', fontsize=12)
    ax.set_title('Parameter Sensitivity: δ vs Success Rate', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "exp1_delta_sensitivity.png"), dpi=150)
    plt.close(fig)
    print(f"  图表已保存: {RESULT_DIR}/exp1_delta_sensitivity.png")

    return results

# ========== 实验2: 纠错码长度 ==========

def experiment2_ecc_length():
    print("\n" + "="*60)
    print("实验2: 纠错码长度 (MSG_LEN, ECC_LEN)")
    print("="*60)

    secret = "cat"
    prompt = "A majestic mountain landscape"
    delta = 2.0
    configs = [(10, 10), (10, 20), (10, 30), (20, 20), (20, 40)]
    n_images = 30

    results = []
    for msg_len, ecc_len in configs:
        total_bits = (msg_len + ecc_len) * 8
        if total_bits > 16384:
            print(f"  跳过 ({msg_len},{ecc_len}): 总比特数 {total_bits} > 16384")
            continue

        clear_cache()
        subdir = os.path.join(RESULT_DIR, f"exp2_m{msg_len}_e{ecc_len}")
        os.makedirs(subdir, exist_ok=True)

        no_att_ok = 0
        jpeg30_ok = 0

        for i in range(n_images):
            out_path = os.path.join(subdir, f"img_{i:04d}.png")
            hide(secret, PRIVATE_IMAGE, prompt, out_path, delta=delta,
                 msg_len=msg_len, ecc_len=ecc_len)

            img = Image.open(out_path).convert("RGB")

            # No attack
            result, ok = extract_safe(img, PRIVATE_IMAGE, prompt,
                                      msg_len=msg_len, ecc_len=ecc_len)
            if ok and result == secret:
                no_att_ok += 1

            # JPEG 30
            jpeg_img = jpeg_compress(img, 30)
            result, ok = extract_safe(jpeg_img, PRIVATE_IMAGE, prompt,
                                      msg_len=msg_len, ecc_len=ecc_len)
            if ok and result == secret:
                jpeg30_ok += 1

        no_rate = no_att_ok / n_images * 100
        jp_rate = jpeg30_ok / n_images * 100
        results.append((msg_len, ecc_len, total_bits, no_att_ok, n_images, no_rate, jpeg30_ok, jp_rate))
        print(f"  ({msg_len},{ecc_len}) bits={total_bits:4d}: no_att={no_rate:.0f}%  jpeg30={jp_rate:.0f}%")

    # Save CSV
    csv_path = os.path.join(RESULT_DIR, "exp2_ecc_length.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["msg_len", "ecc_len", "total_bits", "no_attack_success",
                         "total", "no_attack_rate", "jpeg30_success", "jpeg30_rate"])
        for row in results:
            writer.writerow(row)

    # Table (Markdown)
    md = "| MSG_LEN | ECC_LEN | 总比特数 | 无攻击成功率 | JPEG30成功率 |\n"
    md += "|---------|---------|----------|-------------|-------------|\n"
    for msg_len, ecc_len, total_bits, no_ok, total, no_rate, jp_ok, jp_rate in results:
        md += f"| {msg_len} | {ecc_len} | {total_bits} | {no_rate:.1f}% | {jp_rate:.1f}% |\n"
    print("\n--- Markdown 表格 ---\n" + md)

    return results

# ========== 实验3: 文本长度与内容多样性 ==========

def experiment3_text_diversity():
    print("\n" + "="*60)
    print("实验3: 文本长度与内容多样性")
    print("="*60)

    prompt = "A majestic mountain landscape"
    delta = 2.0
    # Use only short texts that fit within MSG_LEN=10
    secrets = {
        "short_en_3": "cat",
        "short_en_3b": "dog",
        "zh_short": "你好",       # 6 bytes in UTF-8
    }
    n_images = 50

    results = []
    for label, secret in secrets.items():
        clear_cache()
        subdir = os.path.join(RESULT_DIR, f"exp3_{label}")
        os.makedirs(subdir, exist_ok=True)

        no_att_ok = 0
        jpeg50_ok = 0
        gauss15_ok = 0

        # Adjusted delta for Chinese text (more bytes = more bits)
        # Actually with MSG_LEN=10, all secrets fit in 10 bytes
        # Total bits = 240 for all cases
        use_delta = delta

        for i in range(n_images):
            out_path = os.path.join(subdir, f"img_{i:04d}.png")
            try:
                hide(secret, PRIVATE_IMAGE, prompt, out_path, delta=use_delta)
            except Exception as e:
                print(f"  生成失败: {e}")
                continue

            img = Image.open(out_path).convert("RGB")

            # No attack
            result, ok = extract_safe(img, PRIVATE_IMAGE, prompt)
            if ok and result == secret:
                no_att_ok += 1

            # JPEG 50
            jpeg_img = jpeg_compress(img, 50)
            result, ok = extract_safe(jpeg_img, PRIVATE_IMAGE, prompt)
            if ok and result == secret:
                jpeg50_ok += 1

            # Gaussian σ=15
            noise_img = add_gaussian_noise(img, 15)
            result, ok = extract_safe(noise_img, PRIVATE_IMAGE, prompt)
            if ok and result == secret:
                gauss15_ok += 1

        no_rate = no_att_ok / n_images * 100
        jp_rate = jpeg50_ok / n_images * 100
        gn_rate = gauss15_ok / n_images * 100
        results.append((label, secret, len(secret.encode('utf-8')),
                        no_rate, jp_rate, gn_rate))
        print(f"  {label} (\"{secret}\", {len(secret.encode('utf-8'))}B): "
              f"no_att={no_rate:.0f}%  jpeg50={jp_rate:.0f}%  gauss15={gn_rate:.0f}%")

    # Save CSV
    csv_path = os.path.join(RESULT_DIR, "exp3_text_diversity.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["label", "secret", "byte_len", "no_attack_rate",
                         "jpeg50_rate", "gauss15_rate"])
        for row in results:
            writer.writerow(row)

    # Markdown table
    md = "| 类型 | 文本 | 字节数 | 无攻击 | JPEG50 | 高斯σ=15 |\n"
    md += "|------|------|--------|--------|--------|----------|\n"
    for label, secret, blen, nr, jr, gr in results:
        md += f"| {label} | {secret} | {blen} | {nr:.1f}% | {jr:.1f}% | {gr:.1f}% |\n"
    print("\n--- Markdown 表格 ---\n" + md)

    return results

# ========== 实验4: 攻击鲁棒性批量测试 ==========

def experiment4_attack_robustness():
    print("\n" + "="*60)
    print("实验4: 攻击鲁棒性批量测试 (500张图像)")
    print("="*60)

    secrets = ["cat", "dog", "hello", "JNU", "secret"]
    prompts = [
        "A majestic mountain landscape",
        "A cute cat sitting on a windowsill",
        "A beautiful ocean beach scene",
        "A friendly dog running in a park",
        "A colorful bird perched on a branch",
    ]
    delta = 2.8
    n_per = 20  # instances per combination

    jpeg_qualities = [80, 60, 40, 20]
    noise_sigmas = [5, 10, 15, 20]
    crop_scales = [0.9, 0.8, 0.7, 0.6]

    # Stats: attack_type -> secret -> [success_count, total_count]
    jpeg_stats = {q: {s: [0, 0] for s in secrets} for q in jpeg_qualities}
    noise_stats = {sig: {s: [0, 0] for s in secrets} for sig in noise_sigmas}
    crop_stats = {sc: {s: [0, 0] for s in secrets} for sc in crop_scales}
    no_att_stats = {s: [0, 0] for s in secrets}

    total_gen = len(secrets) * len(prompts) * n_per
    count = 0

    for secret in secrets:
        for prompt in prompts:
            clear_cache()
            safe_s = secret.replace("/", "_").replace(" ", "_")
            safe_p = prompt[:20].replace(" ", "_").replace("/", "_")
            subdir = os.path.join(RESULT_DIR, f"exp4_{safe_s}_{safe_p}")
            os.makedirs(subdir, exist_ok=True)

            for i in range(n_per):
                count += 1
                if count % 50 == 0:
                    print(f"  生成进度: {count}/{total_gen}")

                out_path = os.path.join(subdir, f"img_{i:04d}.png")
                try:
                    hide(secret, PRIVATE_IMAGE, prompt, out_path, delta=delta)
                except Exception:
                    continue

                img = Image.open(out_path).convert("RGB")

                # No attack
                result, ok = extract_safe(img, PRIVATE_IMAGE, prompt)
                no_att_stats[secret][1] += 1
                if ok and result == secret:
                    no_att_stats[secret][0] += 1

                # JPEG attacks
                for q in jpeg_qualities:
                    jpeg_img = jpeg_compress(img, q)
                    result, ok = extract_safe(jpeg_img, PRIVATE_IMAGE, prompt)
                    jpeg_stats[q][secret][1] += 1
                    if ok and result == secret:
                        jpeg_stats[q][secret][0] += 1

                # Gaussian noise attacks
                for sig in noise_sigmas:
                    noise_img = add_gaussian_noise(img, sig)
                    result, ok = extract_safe(noise_img, PRIVATE_IMAGE, prompt)
                    noise_stats[sig][secret][1] += 1
                    if ok and result == secret:
                        noise_stats[sig][secret][0] += 1

                # Crop attacks
                for sc in crop_scales:
                    crop_img = random_crop(img, min_scale=sc)
                    result, ok = extract_safe(crop_img, PRIVATE_IMAGE, prompt)
                    crop_stats[sc][secret][1] += 1
                    if ok and result == secret:
                        crop_stats[sc][secret][0] += 1

    # Compute per-attack average success rates
    jpeg_rates = {}
    for q in jpeg_qualities:
        total_ok = sum(jpeg_stats[q][s][0] for s in secrets)
        total_all = sum(jpeg_stats[q][s][1] for s in secrets)
        jpeg_rates[q] = total_ok / total_all * 100 if total_all > 0 else 0

    noise_rates = {}
    for sig in noise_sigmas:
        total_ok = sum(noise_stats[sig][s][0] for s in secrets)
        total_all = sum(noise_stats[sig][s][1] for s in secrets)
        noise_rates[sig] = total_ok / total_all * 100 if total_all > 0 else 0

    crop_rates = {}
    for sc in crop_scales:
        total_ok = sum(crop_stats[sc][s][0] for s in secrets)
        total_all = sum(crop_stats[sc][s][1] for s in secrets)
        crop_rates[sc] = total_ok / total_all * 100 if total_all > 0 else 0

    no_total_ok = sum(no_att_stats[s][0] for s in secrets)
    no_total_all = sum(no_att_stats[s][1] for s in secrets)
    no_rate = no_total_ok / no_total_all * 100 if no_total_all > 0 else 0

    print(f"\n  无攻击: {no_rate:.1f}%")
    print(f"  JPEG: {jpeg_rates}")
    print(f"  高斯噪声: {noise_rates}")
    print(f"  裁剪: {crop_rates}")

    # Save combined CSV
    csv_path = os.path.join(RESULT_DIR, "exp4_attack_robustness.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["attack_type", "parameter", "success", "total", "rate"])
        for q, r in jpeg_rates.items():
            total_ok = sum(jpeg_stats[q][s][0] for s in secrets)
            total_all = sum(jpeg_stats[q][s][1] for s in secrets)
            writer.writerow(["jpeg", q, total_ok, total_all, r])
        for sig, r in noise_rates.items():
            total_ok = sum(noise_stats[sig][s][0] for s in secrets)
            total_all = sum(noise_stats[sig][s][1] for s in secrets)
            writer.writerow(["gaussian", sig, total_ok, total_all, r])
        for sc, r in crop_rates.items():
            total_ok = sum(crop_stats[sc][s][0] for s in secrets)
            total_all = sum(crop_stats[sc][s][1] for s in secrets)
            writer.writerow(["crop", sc, total_ok, total_all, r])

    # Three line charts
    # JPEG
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(jpeg_qualities, [jpeg_rates[q] for q in jpeg_qualities], 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('JPEG Quality', fontsize=12)
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('JPEG Compression Robustness', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "exp4_jpeg.png"), dpi=150)
    plt.close(fig)

    # Gaussian
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(noise_sigmas, [noise_rates[sig] for sig in noise_sigmas], 's-', linewidth=2, markersize=8, color='orange')
    ax.set_xlabel('Gaussian Noise σ', fontsize=12)
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('Gaussian Noise Robustness', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "exp4_gaussian.png"), dpi=150)
    plt.close(fig)

    # Crop
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(crop_scales, [crop_rates[sc] for sc in crop_scales], '^--', linewidth=2, markersize=8, color='green')
    ax.set_xlabel('Crop Retention Ratio', fontsize=12)
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('Random Crop Robustness', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "exp4_crop.png"), dpi=150)
    plt.close(fig)

    print("  图表已保存")

    return jpeg_rates, noise_rates, crop_rates

# ========== 实验5: LSB 对比 ==========

def lsb_hide(secret_text, cover_path, output_path):
    """传统 LSB 隐写：将秘密文本的最低有效位嵌入载体图像"""
    img = Image.open(cover_path).convert("RGB")
    data = secret_text.encode('utf-8')
    # 添加长度头（2字节）+ 数据
    bits_str = ''.join(f'{b:08b}' for b in data)
    # 用 16 位存储长度
    length_bits = f'{len(bits_str):016b}'
    full_bits = length_bits + bits_str

    pixels = np.array(img).reshape(-1, 3)
    if len(full_bits) > len(pixels) * 3:
        raise ValueError("秘密文本太长，图像容量不足")

    for i, bit in enumerate(full_bits):
        ch = i % 3
        px = i // 3
        if bit == '1':
            pixels[px, ch] |= 1
        else:
            pixels[px, ch] &= 254  # clear LSB (avoid ~1 on uint8)

    new_img = Image.fromarray(pixels.reshape(np.array(img).shape))
    new_img.save(output_path)

def lsb_extract(image_path):
    """从 LSB 图像提取秘密文本"""
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)

    # 提取前 16 位的长度信息
    length = 0
    for i in range(16):
        ch = i % 3
        px = i // 3
        length = (length << 1) | (pixels[px, ch] & 1)

    if length <= 0 or length > len(pixels) * 3 - 16:
        raise ValueError("无效的长度信息或容量不足")

    # 提取数据
    bits = []
    for i in range(16, 16 + length):
        ch = i % 3
        px = i // 3
        bits.append(str(pixels[px, ch] & 1))

    data_bytes = bytes(int(''.join(bits[i:i+8]), 2) for i in range(0, len(bits), 8))
    return data_bytes.decode('utf-8')

def experiment5_lsb_comparison():
    print("\n" + "="*60)
    print("实验5: 与 LSB 隐写对比")
    print("="*60)

    secret = "cat"
    prompt = "A majestic mountain landscape"
    delta = 2.8
    n_images = 100

    clear_cache()
    subdir_ours = os.path.join(RESULT_DIR, "exp5_ours")
    subdir_lsb = os.path.join(RESULT_DIR, "exp5_lsb")
    os.makedirs(subdir_ours, exist_ok=True)
    os.makedirs(subdir_lsb, exist_ok=True)

    # 攻击类型
    jpeg_qualities = [70, 50, 30]
    noise_sigma = 10

    our_stats = {"no_attack": 0, "jpeg70": 0, "jpeg50": 0, "jpeg30": 0, "gauss10": 0}
    lsb_stats = {"no_attack": 0, "jpeg70": 0, "jpeg50": 0, "jpeg30": 0, "gauss10": 0}
    total_tested = 0

    for i in range(n_images):
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{n_images}")

        # 我们的方法
        our_path = os.path.join(subdir_ours, f"img_{i:04d}.png")
        hide(secret, PRIVATE_IMAGE, prompt, our_path, delta=delta)

        # LSB 方法 (在我们的含密图像上再做 LSB)
        lsb_path = os.path.join(subdir_lsb, f"img_{i:04d}.png")
        lsb_hide(secret, our_path, lsb_path)

        our_img = Image.open(our_path).convert("RGB")
        lsb_img = Image.open(lsb_path).convert("RGB")

        # 无攻击 - 我们的方法
        result, ok = extract_safe(our_img, PRIVATE_IMAGE, prompt)
        if ok and result == secret:
            our_stats["no_attack"] += 1

        # 无攻击 - LSB
        try:
            result = lsb_extract(lsb_path)
            if result == secret:
                lsb_stats["no_attack"] += 1
        except Exception:
            pass

        # JPEG 攻击
        for q in jpeg_qualities:
            jpeg_our = jpeg_compress(our_img, q)
            jpeg_lsb = jpeg_compress(lsb_img, q)

            result, ok = extract_safe(jpeg_our, PRIVATE_IMAGE, prompt)
            if ok and result == secret:
                our_stats[f"jpeg{q}"] += 1

            try:
                # Save and load LSB after JPEG
                tmp = os.path.join(RESULT_DIR, "exp5_tmp.png")
                jpeg_lsb.save(tmp)
                result = lsb_extract(tmp)
                if result == secret:
                    lsb_stats[f"jpeg{q}"] += 1
            except Exception:
                pass

        # 高斯噪声
        noisy_our = add_gaussian_noise(our_img, noise_sigma)
        noisy_lsb = add_gaussian_noise(lsb_img, noise_sigma)

        result, ok = extract_safe(noisy_our, PRIVATE_IMAGE, prompt)
        if ok and result == secret:
            our_stats["gauss10"] += 1

        tmp_noise = os.path.join(RESULT_DIR, "exp5_tmp_noise.png")
        noisy_lsb.save(tmp_noise)
        try:
            result = lsb_extract(tmp_noise)
            if result == secret:
                lsb_stats["gauss10"] += 1
        except Exception:
            pass

        total_tested += 1

    # 计算成功率
    our_rates = {k: v / total_tested * 100 for k, v in our_stats.items()}
    lsb_rates = {k: v / total_tested * 100 for k, v in lsb_stats.items()}

    print(f"\n  我们方法: {our_rates}")
    print(f"  LSB方法: {lsb_rates}")

    # Save CSV
    csv_path = os.path.join(RESULT_DIR, "exp5_lsb_comparison.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["attack", "our_method_rate", "lsb_rate"])
        for attack in ["no_attack", "jpeg70", "jpeg50", "jpeg30", "gauss10"]:
            writer.writerow([attack, our_rates[attack], lsb_rates[attack]])

    # Markdown table
    md = "| 攻击类型 | 本文方法 | LSB方法 |\n"
    md += "|---------|---------|--------|\n"
    for attack in ["no_attack", "jpeg70", "jpeg50", "jpeg30", "gauss10"]:
        md += f"| {attack} | {our_rates[attack]:.1f}% | {lsb_rates[attack]:.1f}% |\n"
    print("\n--- Markdown 表格 ---\n" + md)

    # Comparison chart
    attacks = ["No Attack", "JPEG 70", "JPEG 50", "JPEG 30", "Gaussian σ=10"]
    our_vals = [our_rates[a] for a in ["no_attack", "jpeg70", "jpeg50", "jpeg30", "gauss10"]]
    lsb_vals = [lsb_rates[a] for a in ["no_attack", "jpeg70", "jpeg50", "jpeg30", "gauss10"]]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(attacks))
    width = 0.35
    ax.bar(x - width/2, our_vals, width, label='Proposed Method', color='steelblue')
    ax.bar(x + width/2, lsb_vals, width, label='LSB', color='salmon')
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('Robustness Comparison: Proposed vs LSB', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(attacks, rotation=15)
    ax.legend()
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "exp5_lsb_comparison.png"), dpi=150)
    plt.close(fig)

    # Clean up temp files
    for f in ["exp5_tmp.png", "exp5_tmp_noise.png"]:
        p = os.path.join(RESULT_DIR, f)
        if os.path.exists(p):
            os.remove(p)

    print("  图表已保存")
    return our_rates, lsb_rates


# ========== 主函数 ==========

def main():
    print("="*60)
    print("大规模鲁棒性实验")
    print(f"结果目录: {RESULT_DIR}")
    print("="*60)

    load_pipe()

    all_results = {}

    # 实验1: 参数敏感性
    results1 = experiment1_delta_sensitivity()
    all_results["exp1"] = results1

    # 实验2: 纠错码长度
    results2 = experiment2_ecc_length()
    all_results["exp2"] = results2

    # 实验3: 文本多样性
    results3 = experiment3_text_diversity()
    all_results["exp3"] = results3

    # 实验4: 攻击鲁棒性
    results4 = experiment4_attack_robustness()
    all_results["exp4"] = results4

    # 实验5: LSB对比
    results5 = experiment5_lsb_comparison()
    all_results["exp5"] = results5

    # Save all results as JSON
    json_path = os.path.join(RESULT_DIR, "all_results.json")
    # Convert non-serializable items
    serializable = {
        "exp1": {str(k): v for k, v in results1.items()},
        "exp4": {
            "jpeg": {str(k): v for k, v in results4[0].items()},
            "gaussian": {str(k): v for k, v in results4[1].items()},
            "crop": {str(k): v for k, v in results4[2].items()},
        },
        "exp5": {"our": results5[0], "lsb": results5[1]},
    }
    with open(json_path, 'w') as f:
        json.dump(serializable, f, indent=2)

    print("\n" + "="*60)
    print("所有实验完成！")
    print(f"结果保存在: {RESULT_DIR}")
    print("="*60)

if __name__ == "__main__":
    main()
