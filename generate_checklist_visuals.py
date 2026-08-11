"""Génère les visuels pour la checklist AI Governance via Gemini 3 Pro Image (Nano Banana Pro)."""
import os
import sys
import base64

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from google import genai
from google.genai import types as genai_types

GCP_PROJECT = "mia-chatbot-veille"

PROMPTS = {
    "checklist-cover": {
        "prompt": """A technical blueprint-style illustration of an AI governance pipeline system. 
Dark navy background (#0b1220). Fine electric blue lines (#3b66f5) forming a schematic diagram showing: 
data nodes (cylinders) flowing into a central AI model core (neural network nodes), 
then branching to deployment (server racks) and monitoring (gauge/dashboard) checkpoints. 
12 numbered control points (01-12) arranged around the pipeline as small circles with numbers in monospace font. 
Style: architectural blueprint, cyanotype aesthetic, minimal, precise, technical. 
White/light gray accents (#f4f6f8) for contrast. No text labels except the numbers 01 through 12. 
Square format, high detail, professional.""",
        "filename": "checklist-cover.png",
    },
    "checklist-pipeline": {
        "prompt": """A minimalist flat illustration of a 5-stage AI governance pipeline, shown left to right:
1. GOVERNANCE (shield icon with checkmark), 
2. DATA (database cylinder with layers), 
3. MODEL (neural network with connected nodes), 
4. DEPLOYMENT (rocket or server with up arrow), 
5. MONITORING (radar/gauge with pulse line).
Each stage is a rounded rectangle card connected by flowing blue arrows. 
Colors: electric blue #3b66f5 for icons and arrows, light gray #f4f6f8 background, 
dark navy #0b1220 for text and card borders. Clean geometric flat design, no gradients, 
professional tech aesthetic. Wide horizontal format. Small numbers (01-12) distributed 
inside the relevant cards. No other text.""",
        "filename": "checklist-pipeline.png",
    },
    "checklist-decor": {
        "prompt": """Abstract geometric pattern suggesting a governance framework: 
interconnected nodes forming a structured mesh network, some nodes highlighted in 
electric blue #3b66f5, others in subtle gray. Dark navy #0b1220 background. 
Minimal, technical, elegant, low opacity feel. Wide format, suitable as a background 
decorative element. No text. Professional, clean, sophisticated.""",
        "filename": "checklist-decor.png",
    },
}


def generate_image(prompt: str, output_path: str) -> bool:
    """Génère une image avec Gemini 3 Pro Image."""
    print(f"  🎨 Génération: {output_path}")
    print(f"  📝 Prompt: {prompt[:100]}...")

    try:
        client = genai.Client(vertexai=True, project=GCP_PROJECT, location="global")
        response = client.models.generate_content(
            model="gemini-3-pro-image",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            print(f"  ❌ Aucune image dans la réponse")
            return False

        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"  ✅ Image sauvegardée: {output_path} ({len(image_bytes)} bytes)")
        return True

    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(output_dir, exist_ok=True)

    print("\n🚀 Génération des visuels Checklist AI Governance\n")

    success = 0
    total = len(PROMPTS)

    for key, config in PROMPTS.items():
        print(f"\n--- {key} ---")
        output_path = os.path.join(output_dir, config["filename"])
        if generate_image(config["prompt"], output_path):
            success += 1

    print(f"\n{'='*50}")
    print(f"✅ {success}/{total} visuels générés avec succès")
    print(f"📁 Output: {output_dir}/")
    if success < total:
        print("⚠️  Certains visuels ont échoué — relance le script pour réessayer")


if __name__ == "__main__":
    main()
