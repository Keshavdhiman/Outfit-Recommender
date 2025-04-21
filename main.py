from flask import Flask, request, jsonify, send_file
import os
import torch
import clip
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# --- Init ---
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, preprocess = clip.load("ViT-B/32", device=device)

app = Flask(__name__)

# --- Helper Functions (Same as your script) ---
def extract_dominant_color(image_path):
    try:
        image = Image.open(image_path).convert("RGB").resize((50, 50))
        pixels = list(image.getdata())
        avg_color = tuple(sum(x) // len(x) for x in zip(*pixels))
        return torch.tensor(avg_color, dtype=torch.float)
    except:
        return torch.tensor([255, 255, 255], dtype=torch.float)

def load_items_from_folder(folder_path, selected_gender, selected_occasion):
    item_db = defaultdict(list)
    paths = defaultdict(list)
    colors = defaultdict(list)

    valid_exts = [".jpg", ".jpeg"]
    for fname in os.listdir(folder_path):
        if not any(fname.lower().endswith(ext) for ext in valid_exts):
            continue

        parts = fname.lower().split("_")
        if len(parts) < 4:
            continue

        category, gender, occasion = parts[0], parts[1], parts[2]
        if selected_gender not in [gender, "unisex"] and gender != "unisex":
            continue
        if selected_occasion != occasion:
            continue

        full_path = os.path.join(folder_path, fname)
        try:
            img = preprocess(Image.open(full_path).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                emb = clip_model.encode_image(img)
                emb /= emb.norm(dim=-1, keepdim=True)
            item_db[category].append(emb.cpu())
            paths[category].append(full_path)
            colors[category].append(extract_dominant_color(full_path))
        except:
            pass

    for cat in item_db:
        item_db[cat] = torch.cat(item_db[cat])
        colors[cat] = torch.stack(colors[cat])

    return item_db, paths, colors

def recommend_outfit(item_db, paths, colors, occasion, gender):
    outfit_plan = {
        "Top": ["top", "tshirt", "blouse", "hoodie","shirt"],
        "Bottom": ["jeans", "trousers", "bottom", "skirt","pants"],
        "Coat": ["coat", "jacket"],
        "Shoes": ["shoes", "heels", "sneakers"],
        "Accessories": ["accessories", "jewelry", "handbag", "watch", "sunglasses", "bracelet"]
    }

    selected_items = []
    selected_colors = []

    for group, candidates in outfit_plan.items():
        best_score = -1
        selected_path = None
        selected_color = None

        for cat in candidates:
            if cat not in item_db:
                continue

            prompt = f"{gender} {occasion} {cat}"
            text = clip.tokenize([prompt]).to(device)
            with torch.no_grad():
                text_emb = clip_model.encode_text(text)
                text_emb /= text_emb.norm(dim=-1, keepdim=True)

            sims = cosine_similarity(text_emb.cpu().numpy(), item_db[cat].cpu().numpy())[0]

            if selected_colors:
                avg_ref_color = torch.stack(selected_colors).mean(dim=0)
                color_diffs = torch.norm(colors[cat] - avg_ref_color, dim=1)
                color_sims = 1 / (1 + color_diffs)
            else:
                color_sims = torch.ones_like(torch.tensor(sims))

            final_scores = sims * color_sims.numpy()
            best_idx = final_scores.argmax()
            selected_path = paths[cat][best_idx]
            selected_color = colors[cat][best_idx]
            break

        selected_items.append(selected_path)
        if selected_color is not None:
            selected_colors.append(selected_color)

    return selected_items

def create_outfit_image(image_paths, output_path="final_outfit.jpg"):
    images = [Image.open(p).convert("RGBA") for p in image_paths if p]
    if not images:
        return None

    target_size = (400, 400)
    resized = []
    for img in images:
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        resized.append(img)

    cols, rows = 2, 2
    box_w, box_h = target_size
    padding = 40
    final_w = cols * box_w + (cols + 1) * padding
    final_h = rows * box_h + (rows + 1) * padding

    collage = Image.new("RGBA", (final_w, final_h), (255, 255, 255, 255))

    for idx, img in enumerate(resized[:4]):
        row, col = divmod(idx, cols)
        x = padding + col * (box_w + padding)
        y = padding + row * (box_h + padding)
        collage.paste(img, (x + (box_w - img.width)//2, y + (box_h - img.height)//2), img)

    collage.convert("RGB").save(output_path)
    return output_path

# --- API Endpoint ---
@app.route("/analyze_audio", methods=["POST"])
def analyze_audio():  # You can rename this to /recommend_outfit if more relevant
    data = request.get_json()
    occasion = data.get("occasion")
    gender = data.get("gender")

    if not occasion or not gender:
        return jsonify({"error": "Missing occasion or gender"}), 400

    try:
        item_db, paths, colors = load_items_from_folder("wardrobe", gender, occasion)
        outfit = recommend_outfit(item_db, paths, colors, occasion, gender)
        collage_path = create_outfit_image(outfit)

        response = {
            "outfit": [os.path.basename(p) if p else None for p in outfit],
            "collage_image": collage_path
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Run Server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
