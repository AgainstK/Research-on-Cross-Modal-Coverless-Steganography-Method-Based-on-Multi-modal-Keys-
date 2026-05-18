#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用隐写：支持任意秘密文本和公钥提示词
私钥: 图像 + 固定文本（控制嵌入位置）
公钥: 用户输入的 prompt
"""

import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler
from reedsolo import RSCodec
import hashlib
import numpy as np
from PIL import Image
import argparse
import os

# ========== RS 配置 ==========
MSG_LEN = 10       # 原始消息最大字节数（可容纳10个英文字符或约3个汉字）
ECC_LEN = 20       # 纠错码字节数，总长30字节，可纠10个符号错误

_rs_cache: dict = {}

def get_rs(ecc_len: int):
    """Get or create a cached RSCodec instance for the given ECC length"""
    if ecc_len not in _rs_cache:
        _rs_cache[ecc_len] = RSCodec(ecc_len)
    return _rs_cache[ecc_len]


def text_to_bits(text: str, msg_len: int = MSG_LEN, ecc_len: int = ECC_LEN) -> str:
    """将文本编码为 RS 码并转换为二进制串"""
    data = text.encode('utf-8')[:msg_len].ljust(msg_len, b'\0')
    encoded = get_rs(ecc_len).encode(data)
    return ''.join(f'{b:08b}' for b in encoded)


def bits_to_text(bits: str, ecc_len: int = ECC_LEN) -> str:
    """从二进制串解码恢复文本"""
    if len(bits) % 8:
        bits = bits.ljust((len(bits) + 7) // 8 * 8, '0')
    data = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
    decoded, _, _ = get_rs(ecc_len).decode(data)
    return decoded.rstrip(b'\0').decode('utf-8')

def get_indices(private_img_path: str, secret_seed: str, total_bits: int):
    """私钥图像 + 私钥文本 → 确定性的嵌入位置序列"""
    with open(private_img_path, 'rb') as f:
        img_hash = hashlib.sha256(f.read()).digest()
    text_hash = hashlib.sha256(secret_seed.encode()).digest()
    seed_bytes = hashlib.sha256(img_hash + text_hash).digest()
    seed = int.from_bytes(seed_bytes[:8], 'little') & 0x7fffffff
    np.random.seed(seed)
    total_elements = 4 * 64 * 64
    return np.random.permutation(total_elements)[:total_bits].tolist()

# ========== 模型加载（单例） ==========
pipe = None
def load_pipe():
    global pipe
    if pipe is None:
        print("Loading Stable Diffusion...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
            safety_checker=None
        ).to("cuda")
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
        print("Model ready.")

def hide(secret_text, private_image_path, public_prompt, output_path, delta=2.0,
         num_inference_steps=50, guidance_scale=7.5,
         msg_len=MSG_LEN, ecc_len=ECC_LEN):
    load_pipe()
    bits = text_to_bits(secret_text, msg_len=msg_len, ecc_len=ecc_len)
    indices = get_indices(private_image_path, "mykey", len(bits))
    generator = torch.Generator("cuda").manual_seed(42)
    latents = torch.randn((1,4,64,64), generator=generator, device="cuda", dtype=torch.float16)
    flat = latents.view(-1)
    for i, idx in enumerate(indices):
        flat[idx] = delta if bits[i]=='1' else -delta
    latents = flat.view(1,4,64,64)
    img = pipe(prompt=public_prompt, latents=latents, num_inference_steps=num_inference_steps,
               guidance_scale=guidance_scale).images[0]
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    img.save(output_path)
    print(f"Encrypted image saved to {output_path}")

def _vae_encode(img_pil: Image.Image):
    """VAE encode a PIL image to latent space"""
    img_tensor = (torch.tensor(np.array(img_pil), dtype=torch.float16).permute(2, 0, 1).unsqueeze(0).to("cuda") / 127.5) - 1.0
    with torch.no_grad():
        return pipe.vae.encode(img_tensor).latent_dist.mean * pipe.vae.config.scaling_factor


def _generate_clean_reference(private_image_path: str, public_prompt: str, num_inference_steps: int = 50,
                              guidance_scale: float = 7.5, seed: int = 42):
    """Generate a clean reference image (no hidden data) for differential extraction"""
    generator = torch.Generator("cuda").manual_seed(seed)
    latents = torch.randn((1, 4, 64, 64), generator=generator, device="cuda", dtype=torch.float16)
    return pipe(prompt=public_prompt, latents=latents,
                num_inference_steps=num_inference_steps, guidance_scale=guidance_scale).images[0]


_clean_ref_cache: dict = {}  # key: (public_prompt, num_inference_steps, guidance_scale) -> VAE latent


def _reveal_by_reference(test_img: Image.Image, private_image_path: str, public_prompt: str,
                         num_inference_steps: int = 50, guidance_scale: float = 7.5,
                         msg_len: int = MSG_LEN, ecc_len: int = ECC_LEN) -> str:
    """Extract hidden bits by comparing test image VAE encoding against a clean reference"""
    cache_key = (public_prompt, num_inference_steps, guidance_scale)
    if cache_key not in _clean_ref_cache:
        clean_img = _generate_clean_reference(private_image_path, public_prompt,
                                              num_inference_steps=num_inference_steps,
                                              guidance_scale=guidance_scale)
        _clean_ref_cache[cache_key] = _vae_encode(clean_img)
    z_clean = _clean_ref_cache[cache_key]
    z_test = _vae_encode(test_img)
    diff = z_test - z_clean
    flat_diff = diff.view(-1)

    total_bits = (msg_len + ecc_len) * 8
    indices = get_indices(private_image_path, "mykey", total_bits)
    bits_str = ''.join('1' if flat_diff[idx] > 0 else '0' for idx in indices)
    secret = bits_to_text(bits_str, ecc_len=ecc_len)
    return secret


def reveal(image_path, private_image_path, public_prompt,
           num_inference_steps: int = 50, guidance_scale: float = 7.5,
           msg_len: int = MSG_LEN, ecc_len: int = ECC_LEN):
    load_pipe()
    img = Image.open(image_path).convert("RGB").resize((512, 512))

    # === Primary method: reference comparison (more robust against CFG inversion error) ===
    try:
        secret = _reveal_by_reference(img, private_image_path, public_prompt,
                                      num_inference_steps=num_inference_steps,
                                      guidance_scale=guidance_scale,
                                      msg_len=msg_len, ecc_len=ecc_len)
        print(f"Extracted secret: {secret}")
        return secret
    except Exception:
        pass

    # === Fallback: DDIM inversion ===
    img_tensor = (torch.tensor(np.array(img), dtype=torch.float16).permute(2, 0, 1).unsqueeze(0).to("cuda") / 127.5) - 1.0
    with torch.no_grad():
        z0 = pipe.vae.encode(img_tensor).latent_dist.mean * pipe.vae.config.scaling_factor

    pipe.scheduler.set_timesteps(num_inference_steps, device="cuda")
    timesteps = pipe.scheduler.timesteps

    max_len = pipe.tokenizer.model_max_length
    text_input = pipe.tokenizer([public_prompt], padding="max_length", max_length=max_len, truncation=True, return_tensors="pt").input_ids.to("cuda")
    text_emb = pipe.text_encoder(text_input)[0]
    uncond_input = pipe.tokenizer([""], padding="max_length", max_length=max_len, truncation=True, return_tensors="pt").input_ids.to("cuda")
    uncond_emb = pipe.text_encoder(uncond_input)[0]
    context = torch.cat([uncond_emb, text_emb], dim=0)

    inv_lat = z0.clone()
    timesteps_rev = timesteps.flip(0)
    for i, t in enumerate(timesteps_rev):
        with torch.no_grad():
            latent_model_input = torch.cat([inv_lat] * 2)
            noise_pred = pipe.unet(latent_model_input, t, encoder_hidden_states=context).sample
            noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
            noise_pred = noise_pred_uncond + guidance_scale * (noise_pred_text - noise_pred_uncond)
        alpha_t = pipe.scheduler.alphas_cumprod[t]
        pred_x0 = (inv_lat - (1 - alpha_t)**0.5 * noise_pred) / (alpha_t**0.5 + 1e-8)
        if i < len(timesteps_rev) - 1:
            t_prev = timesteps_rev[i + 1]
            alpha_prev = pipe.scheduler.alphas_cumprod[t_prev]
        else:
            alpha_prev = torch.tensor(1.0, device="cuda", dtype=torch.float16)
        inv_lat = (alpha_prev**0.5) * pred_x0 + (1 - alpha_prev)**0.5 * noise_pred

    total_bits = (msg_len + ecc_len) * 8
    indices = get_indices(private_image_path, "mykey", total_bits)
    flat = inv_lat.view(-1)
    bits_str = ''.join('1' if flat[idx] > 0 else '0' for idx in indices)
    secret = bits_to_text(bits_str, ecc_len=ecc_len)
    print(f"Extracted secret: {secret}")
    return secret

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hide")
    h.add_argument("--secret", required=True, help="要隐藏的文本")
    h.add_argument("--private_image", required=True, help="私钥图像路径")
    h.add_argument("--prompt", required=True, help="公钥文本提示词")
    h.add_argument("--output", default="RESULT/enc.png")
    h.add_argument("--delta", type=float, default=2.0)
    r = sub.add_parser("reveal")
    r.add_argument("--image", required=True)
    r.add_argument("--private_image", required=True)
    r.add_argument("--prompt", required=True)
    args = parser.parse_args()
    if args.cmd == "hide":
        hide(args.secret, args.private_image, args.prompt, args.output, args.delta)
    else:
        reveal(args.image, args.private_image, args.prompt)