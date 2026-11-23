"""Generate a small synthetic labeled review dataset at data/reviews.csv.

Deterministic (seed 42). Produces a CSV with columns: text,label where
label is one of: positive | neutral | negative.

Replace this file with a real dataset (e.g. an Amazon reviews export)
using the same two-column format to train on real data.
"""
import csv
import random
from collections import Counter
from pathlib import Path

random.seed(42)

PRODUCTS = [
    "headphones", "keyboard", "mouse", "charger", "backpack", "water bottle",
    "blender", "desk lamp", "webcam", "phone case", "speaker", "laptop stand",
]

ASPECTS = [
    "battery life", "sound quality", "build quality", "customer service",
    "shipping speed", "design", "materials", "screen", "noise cancelling",
    "comfort",
]

POSITIVE_TEMPLATES = [
    "Absolutely love this {product}! It exceeded my expectations.",
    "Great {product} for the price, highly recommend it.",
    "The {aspect} is fantastic, best purchase this year.",
    "Works perfectly and the {aspect} is impressive.",
    "Very satisfied with this {product}, five stars.",
    "Excellent quality, I use this {product} every day.",
    "Really happy with my {product}, the {aspect} is top notch.",
    "This {product} is amazing, worth every penny.",
    "Impressive {product}, the {aspect} blew me away.",
    "Perfect! Fast delivery and the {product} works great.",
    "The {aspect} is outstanding, I would buy it again.",
    "Love it. Great {product} with solid {aspect}.",
]

NEGATIVE_TEMPLATES = [
    "Terrible {product}, it broke after two days.",
    "Complete waste of money, very disappointed.",
    "The {aspect} is awful and it stopped working within a week.",
    "Poor quality {product}, I would not recommend it to anyone.",
    "Very disappointed with the {aspect}, returning it immediately.",
    "Cheap materials and terrible customer service, avoid this {product}.",
    "Does not work as advertised, total waste of money.",
    "Worst {product} I have ever bought, the {aspect} is horrible.",
    "Broken on arrival and customer service ignored my emails.",
    "Do not buy this {product}, the {aspect} is unacceptable.",
    "I regret this purchase, cheap and badly made.",
    "The {aspect} is pathetic, this {product} is a scam.",
]

NEUTRAL_TEMPLATES = [
    "The {product} arrived on time, it is okay.",
    "It does what it says, nothing special about this {product}.",
    "Average {product}, the {aspect} is acceptable.",
    "Meets basic expectations, no complaints or praise.",
    "Standard {product}, as described in the listing.",
    "It works, though the {aspect} could be better.",
    "Decent {product} for everyday use, nothing more.",
    "The {product} is fine, the {aspect} is average.",
    "Received the {product} in good condition, it is alright.",
    "An okay {product}, does the job but nothing remarkable.",
    "Not bad, not great, just an average {product}.",
    "The {aspect} is acceptable, packaging was fine.",
]

PLAN = [
    ("positive", POSITIVE_TEMPLATES, 1300),
    ("negative", NEGATIVE_TEMPLATES, 1300),
    ("neutral", NEUTRAL_TEMPLATES, 1000),
]


def main():
    rows = []
    for label, templates, count in PLAN:
        for _ in range(count):
            template = random.choice(templates)
            text = template.format(
                product=random.choice(PRODUCTS),
                aspect=random.choice(ASPECTS),
            )
            rows.append((text, label))

    random.shuffle(rows)

    out_path = Path(__file__).resolve().parent / "reviews.csv"
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["text", "label"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Class distribution: {dict(Counter(label for _, label in rows))}")


if __name__ == "__main__":
    main()
