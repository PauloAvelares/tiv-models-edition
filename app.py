

import os
import io
import base64
import requests

from flask import Flask, request, render_template_string, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

STABILITY_API_KEY = os.environ.get("STABILITY_API_KEY")

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TIV Models Edition</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    padding: 30px 16px;
    background: #111;
    color: #fff;
    font-family: Arial, sans-serif;
}
.container {
    max-width: 650px;
    margin: auto;
    background: #1c1c1c;
    padding: 28px;
    border-radius: 16px;
}
h1 { text-align: center; margin-bottom: 5px; }
.subtitle {
    text-align: center;
    color: #bbb;
    margin-bottom: 28px;
}
label {
    display: block;
    margin: 18px 0 8px;
    font-weight: bold;
}
input, select, button {
    width: 100%;
    padding: 13px;
    border-radius: 8px;
    border: 1px solid #444;
    background: #292929;
    color: white;
    font-size: 15px;
}
button {
    margin-top: 24px;
    border: none;
    background: linear-gradient(90deg, #d946ef, #8b5cf6);
    font-weight: bold;
    cursor: pointer;
}
button:hover { opacity: .9; }
.note {
    color: #aaa;
    font-size: 13px;
    line-height: 1.5;
    margin-top: 18px;
}
.error {
    background: #542222;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 15px;
}
</style>
</head>
<body>
<div class="container">
    <h1>TIV Models Edition</h1>
    <div class="subtitle">Editor profissional de fotografias com IA</div>

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}

    <form method="POST" action="/editar" enctype="multipart/form-data">
        <label>Escolha sua fotografia</label>
        <input type="file" name="foto" accept="image/png,image/jpeg" required>

        <label>Intensidade do retoque</label>
        <select name="intensidade">
            <option value="suave">Suave natural</option>
            <option value="moderada" selected>Moderada</option>
            <option value="intensa">Mais intensa</option>
        </select>

        <button type="submit">EDITAR FOTOGRAFIA</button>
    </form>

    <div class="note">
        O objetivo é melhorar iluminação, cores e qualidade,
        preservando a identidade, o rosto, a anatomia e as
        características originais do modelo.
        <br><br>
        Protótipo TIV Models Edition — versão 0.1
    </div>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def inicio():
    return render_template_string(HTML)

@app.route("/editar", methods=["POST"])
def editar():
    if not STABILITY_API_KEY:
        return render_template_string(
            HTML, error="A chave STABILITY_API_KEY não foi configurada no Render."
        )

    foto = request.files.get("foto")
    intensidade = request.form.get("intensidade", "moderada")

    if not foto or not foto.filename:
        return render_template_string(HTML, error="Selecione uma fotografia.")

    if foto.mimetype not in ("image/jpeg", "image/png"):
        return render_template_string(
            HTML, error="Envie uma imagem JPG ou PNG."
        )

    imagem = foto.read()

    if not imagem:
        return render_template_string(HTML, error="O arquivo está vazio.")

    prompts = {
        "suave": (
            "Professional natural photo enhancement, improve lighting, "
            "white balance, color accuracy, clarity and subtle noise reduction. "
            "Preserve exact identity, face, anatomy, body proportions and "
            "original appearance. Natural skin texture."
        ),
        "moderada": (
            "Professional editorial photography retouching, balanced lighting, "
            "color correction, improved sharpness, subtle skin refinement "
            "while preserving natural pores and texture. Preserve exact identity, "
            "face, anatomy and body proportions."
        ),
        "intensa": (
            "High quality professional editorial photo enhancement, stronger "
            "lighting and color correction, refined details and controlled "
            "skin retouching. Preserve exact identity, facial features, anatomy "
            "and body proportions. No facial changes."
        )
    }

    prompt = prompts.get(intensidade, prompts["moderada"])

    try:
        response = requests.post(
            "https://api.stability.ai/v1/generation/"
            "stable-diffusion-xl-1024-v1-0/image-to-image",
            headers={
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Accept": "application/json"
            },
            files={
                "init_image": (
                    foto.filename,
                    imagem,
                    foto.mimetype
                )
            },
            data={
                "text_prompts[0][text]": prompt,
                "text_prompts[0][weight]": 1,
                "text_prompts[1][text]": (
                    "different person, changed face, distorted anatomy, "
                    "extra limbs, plastic skin, artificial appearance"
                ),
                "text_prompts[1][weight]": -1,
                "image_strength": 0.25,
                "cfg_scale": 7,
                "samples": 1,
                "steps": 30
            },
            timeout=180
        )

        if response.status_code != 200:
            return render_template_string(
                HTML,
                error=(
                    "A Stability AI retornou um erro: "
                    + response.text[:500]
                )
            )

        resultado = response.json()
        imagem_base64 = resultado["artifacts"][0]["base64"]
        imagem_final = base64.b64decode(imagem_base64)

        return send_file(
            io.BytesIO(imagem_final),
            mimetype="image/png",
            as_attachment=False,
            download_name="tiv-models-edition.png"
        )

    except requests.exceptions.Timeout:
        return render_template_string(
            HTML, error="A edição demorou demais. Tente novamente."
        )
    except Exception as e:
        return render_template_string(
            HTML, error="Erro durante a edição: " + str(e)
        )

@app.errorhandler(413)
def arquivo_grande(error):
    return render_template_string(
        HTML, error="A imagem ultrapassa o limite de 12 MB."
    ), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
