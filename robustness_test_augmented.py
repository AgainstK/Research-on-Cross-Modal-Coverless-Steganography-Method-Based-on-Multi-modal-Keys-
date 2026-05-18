#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鲁棒性测试：读取上一步生成的实例元数据，对每个含密图像进行攻击并测试提取准确率
- 支持 JPEG 压缩（多种质量）和随机裁剪
- 根据元数据中记录的 prompt 进行解密
"""

import os
import sys
import csv
import random
import io
from PIL import Image
from stego_working import reveal, load_pipe

# ==================== 配置 ====================
PRIVATE_IMAGE = "private_cat.jpg"
INSTANCE_DIR = "RESULT/1000_instances"
METADATA_CSV = os.path.join(INSTANCE_DIR, "instances_metadata.csv")
ATTACKS = {
    "no_attack": {},
    "jpeg_70": {"quality": 70},
    "jpeg_50": {"quality": 50},
    "jpeg_30": {"quality": 30},
    "random_crop": {"min_scale": 0.7},
}

def jpeg_compress(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert('RGB')

def random_crop(image, min_scale=0.7, target_size=(512,512)):
    w, h = image.size
    scale = random.uniform(min_scale, 1.0)
    new_w, new_h = int(w*scale), int(h*scale)
    left = random.randint(0, w - new_w)
    top = random.randint(0, h - new_h)
    cropped = image.crop((left, top, left+new_w, top+new_h))
    return cropped.resize(target_size, Image.LANCZOS)

def main():
    if not os.path.exists(METADATA_CSV):
        print(f"错误: 未找到元数据文件 {METADATA_CSV}")
        return
    
    load_pipe()
    
    # 读取元数据
    instances = []
    with open(METADATA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['output_path'].startswith('FAILED'):
                continue
            instances.append({
                "id": int(row['instance_id']),
                "prompt": row['prompt'].strip(),   # 关键：去除空白
                "output_path": row['output_path']
            })
    
    print(f"共读取 {len(instances)} 个有效实例")
    
    # 统计字典
    stats = {attack: {"success": 0, "total": 0} for attack in ATTACKS}
    
    for item in instances:
        img_path = item['output_path']
        prompt = item['prompt']
        print(f"\n测试实例 {item['id']}: {img_path}")
        stego_img = Image.open(img_path).convert("RGB")
        
        # 无攻击
        try:
            extracted = reveal(img_path, PRIVATE_IMAGE, prompt)
            if extracted == "JiNanDaXue":
                stats["no_attack"]["success"] += 1
        except:
            pass
        stats["no_attack"]["total"] += 1
        
        # JPEG 攻击
        for attack_name, params in ATTACKS.items():
            if attack_name == "no_attack":
                continue
            if attack_name.startswith("jpeg"):
                quality = params["quality"]
                attacked = jpeg_compress(stego_img, quality)
                temp_path = os.path.join(INSTANCE_DIR, f"temp_{item['id']}_{attack_name}.jpg")
                attacked.save(temp_path)
                try:
                    extracted = reveal(temp_path, PRIVATE_IMAGE, prompt)
                    if extracted == "cat":
                        stats[attack_name]["success"] += 1
                except:
                    pass
                stats[attack_name]["total"] += 1
                os.remove(temp_path)
            elif attack_name == "random_crop":
                attacked = random_crop(stego_img, min_scale=params["min_scale"])
                temp_path = os.path.join(INSTANCE_DIR, f"temp_{item['id']}_crop.png")
                attacked.save(temp_path)
                try:
                    extracted = reveal(temp_path, PRIVATE_IMAGE, prompt)
                    if extracted == "cat":
                        stats["random_crop"]["success"] += 1
                except:
                    pass
                stats["random_crop"]["total"] += 1
                os.remove(temp_path)
        
        # 每10个打印一次中间结果
        if item['id'] % 10 == 0:
            print("\n--- 当前统计 ---")
            for k, v in stats.items():
                if v['total'] > 0:
                    rate = v['success'] / v['total'] * 100
                    print(f"{k:12s}: {v['success']}/{v['total']} ({rate:.2f}%)")
            print("----------------")
    
    # 最终输出
    print("\n========== 鲁棒性测试结果 ==========")
    for k, v in stats.items():
        if v['total'] == 0: continue
        rate = v['success'] / v['total'] * 100
        print(f"{k:12s}: {v['success']}/{v['total']} 成功, 成功率 = {rate:.2f}%")

if __name__ == "__main__":
    main()