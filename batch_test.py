#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试：对 batch_generate.py 生成的所有图像进行攻击测试，统计提取成功率。
支持 JPEG 压缩、高斯噪声、随机裁剪。
"""

import os
import csv
import io
import random
import numpy as np
from PIL import Image
from stego_working import reveal, load_pipe
import shutil

METADATA_CSV = "RESULT/batch_experiment/metadata.csv"
PRIVATE_IMAGE = "private_cat.jpg"
ATTACKS = {
    "no_attack": {},
    "jpeg_70": {"quality": 70},
    "jpeg_50": {"quality": 50},
    "jpeg_30": {"quality": 30},
    "gaussian_noise_10": {"sigma": 10},
    "gaussian_noise_20": {"sigma": 20},
    "random_crop": {"min_scale": 0.7},
}
TEMP_DIR = "temp_attack"

def jpeg_compress(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert('RGB')

def add_gaussian_noise(image, sigma=10):
    img_np = np.array(image, dtype=np.float32)
    noise = np.random.normal(0, sigma, img_np.shape)
    noisy = img_np + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)

def random_crop(image, min_scale=0.7, target_size=(512,512)):
    w, h = image.size
    scale = random.uniform(min_scale, 1.0)
    new_w, new_h = int(w*scale), int(h*scale)
    left = random.randint(0, w - new_w) if w > new_w else 0
    top = random.randint(0, h - new_h) if h > new_h else 0
    cropped = image.crop((left, top, left+new_w, top+new_h))
    return cropped.resize(target_size, Image.LANCZOS)

def main():
    if not os.path.exists(METADATA_CSV):
        print(f"错误：未找到元数据文件 {METADATA_CSV}")
        return

    load_pipe()
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 读取元数据
    images = []
    with open(METADATA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            images.append({
                "path": row["image_path"],
                "secret": row["secret"],
                "prompt": row["prompt"]
            })
    print(f"共加载 {len(images)} 张含密图像")

    secrets = set(img["secret"] for img in images)
    stats = {s: {a: {"success": 0, "total": 0} for a in ATTACKS} for s in secrets}

    for idx, img_info in enumerate(images, start=1):
        path = img_info["path"]
        secret = img_info["secret"]
        prompt = img_info["prompt"]
        print(f"\n[{idx}/{len(images)}] 测试 {path} (秘密: {secret})")

        if not os.path.exists(path):
            print(f"  文件不存在，跳过")
            continue

        stego_img = Image.open(path).convert("RGB")

        # 无攻击
        try:
            extracted = reveal(path, PRIVATE_IMAGE, prompt)
            if extracted == secret:
                stats[secret]["no_attack"]["success"] += 1
            else:
                print(f"  无攻击: 期望 '{secret}', 得到 '{extracted}'")
        except Exception as e:
            print(f"  无攻击异常: {e}")
        stats[secret]["no_attack"]["total"] += 1

        # 各种攻击
        for attack_name, params in ATTACKS.items():
            if attack_name == "no_attack":
                continue
            if attack_name.startswith("jpeg"):
                quality = params["quality"]
                attacked = jpeg_compress(stego_img, quality)
                temp_path = os.path.join(TEMP_DIR, f"temp_{idx}_{attack_name}.jpg")
                attacked.save(temp_path)
                try:
                    extracted = reveal(temp_path, PRIVATE_IMAGE, prompt)
                    if extracted == secret:
                        stats[secret][attack_name]["success"] += 1
                    else:
                        print(f"  {attack_name}: 期望 '{secret}', 得到 '{extracted}'")
                except Exception as e:
                    print(f"  {attack_name} 异常: {e}")
                stats[secret][attack_name]["total"] += 1
                os.remove(temp_path)
            elif attack_name.startswith("gaussian_noise"):
                sigma = params["sigma"]
                attacked = add_gaussian_noise(stego_img, sigma)
                temp_path = os.path.join(TEMP_DIR, f"temp_{idx}_{attack_name}.png")
                attacked.save(temp_path)
                try:
                    extracted = reveal(temp_path, PRIVATE_IMAGE, prompt)
                    if extracted == secret:
                        stats[secret][attack_name]["success"] += 1
                    else:
                        print(f"  {attack_name}: 期望 '{secret}', 得到 '{extracted}'")
                except Exception as e:
                    print(f"  {attack_name} 异常: {e}")
                stats[secret][attack_name]["total"] += 1
                os.remove(temp_path)
            elif attack_name == "random_crop":
                attacked = random_crop(stego_img, min_scale=params["min_scale"])
                temp_path = os.path.join(TEMP_DIR, f"temp_{idx}_crop.png")
                attacked.save(temp_path)
                try:
                    extracted = reveal(temp_path, PRIVATE_IMAGE, prompt)
                    if extracted == secret:
                        stats[secret]["random_crop"]["success"] += 1
                    else:
                        print(f"  random_crop: 期望 '{secret}', 得到 '{extracted}'")
                except Exception as e:
                    print(f"  random_crop 异常: {e}")
                stats[secret]["random_crop"]["total"] += 1
                os.remove(temp_path)

        if idx % 10 == 0:
            print("\n--- 中间统计 ---")
            for s in secrets:
                for a in ATTACKS:
                    v = stats[s][a]
                    if v['total'] > 0:
                        print(f"{s} / {a}: {v['success']}/{v['total']} ({100*v['success']/v['total']:.1f}%)")
            print("----------------")

    # 最终输出表格
    print("\n========== 批量实验结果汇总 ==========")
    print("秘密文本\t攻击类型\t成功/总数\t成功率(%)")
    for s in sorted(secrets):
        for a in ATTACKS:
            v = stats[s][a]
            if v['total'] == 0:
                continue
            rate = v['success'] / v['total'] * 100
            print(f"{s}\t{a}\t{v['success']}/{v['total']}\t{rate:.1f}")

    # 清理临时目录
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()