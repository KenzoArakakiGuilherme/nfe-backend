from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)  # Libera CORS para o frontend

def extrair_dados(texto, nome_arquivo):
    linhas = texto.split("\n")
    resultado = []
    i = 0

    while i < len(linhas):
        linha = linhas[i].strip()
        partes = linha.split()

        if re.match(r"^\d{6,}$", partes[0]) and len(partes) >= 16:
            try:
                campos_finais = partes[-15:]
                descricao_raw = " ".join(partes[1:-15])

                # Junta linha de baixo se não for novo produto
                if i + 1 < len(linhas):
                    proxima = linhas[i + 1].strip()
                    if not re.match(r"^\d{6,}", proxima):
                        descricao_raw += " " + proxima
                        i += 1

                resultado.append({
                    "codigo": partes[0],
                    "descricao": descricao_raw,
                    "ncm": campos_finais[0],
                    "cst": campos_finais[1],
                    "cfop": campos_finais[2],
                    "unid": campos_finais[3],
                    "qtd": campos_finais[4],
                    "vlr_unit": campos_finais[5],
                    "vlr_desc": campos_finais[6],
                    "vlr_total": campos_finais[7],
                    "bc_icms": campos_finais[8],
                    "vlr_icms": campos_finais[9],
                    "vlr_ipi": campos_finais[10],
                    "aliq_icms": campos_finais[11],
                    "aliq_ipi": campos_finais[12],
                    "arquivo": nome_arquivo,
                    "data_emissao": extrair_data_emissao(texto)
                })
            except Exception as e:
                print(f"[ERRO] Linha ignorada: {linha}\n{e}")
        i += 1

    return resultado

def extrair_data_emissao(texto):
    match = re.search(r"DATA DA EMISSÃO\s+(\d{2}/\d{2}/\d{4})", texto)
    if match:
        return match.group(1)
    return ""

@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        with pdfplumber.open(arquivo) as pdf:
            texto = "\n".join([page.extract_text() for page in pdf.pages])
        dados = extrair_dados(texto, arquivo.filename)
        all_dados.extend(dados)

    if not all_dados:
        return jsonify([])

    colunas_ordenadas = [
        "codigo", "descricao", "ncm", "cst", "cfop", "unid", "qtd", "vlr_unit",
        "vlr_desc", "vlr_total", "bc_icms", "vlr_icms", "vlr_ipi",
        "aliq_icms", "aliq_ipi", "arquivo", "data_emissao"
    ]

    df = pd.DataFrame(all_dados)[colunas_ordenadas]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False)
    app.config["ULTIMO_ARQUIVO"] = temp_file.name

    return jsonify(all_dados)

@app.route("/baixar")
def baixar_excel():
    arquivo = app.config.get("ULTIMO_ARQUIVO")
    if arquivo and os.path.exists(arquivo):
        return send_file(arquivo, as_attachment=True, download_name="resultado.xlsx")
    return "Nenhum arquivo gerado ainda.", 404

@app.route("/")
def home():
    return "✅ API NFe está no ar!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
