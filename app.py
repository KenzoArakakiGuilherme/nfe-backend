from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)

def extrair_data_emissao(texto):
    match = re.search(r'DATA DA EMISSÃO\s+(\d{2}/\d{2}/\d{4})', texto)
    if match:
        return match.group(1)
    return ""

def extrair_dados(texto, nome_arquivo):
    linhas = texto.split('\n')
    dados_produtos = []
    data_emissao = extrair_data_emissao(texto)

    for linha in linhas:
        if re.match(r"^\d{6,}", linha) and "," in linha:
            partes = linha.strip().split()
            try:
                campos_finais = partes[-13:]  # Últimos 13 campos fixos
                codigo = partes[0]
                descricao = " ".join(partes[1:-13])

                dados_produtos.append({
                    "arquivo": nome_arquivo,
                    "data_emissao": data_emissao,
                    "codigo": codigo,
                    "descricao": descricao,
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
                })
            except Exception:
                continue
    return dados_produtos

@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        nome_arquivo = arquivo.filename
        with pdfplumber.open(arquivo) as pdf:
            texto = "".join([page.extract_text() for page in pdf.pages])
        dados = extrair_dados(texto, nome_arquivo)
        all_dados.extend(dados)

    df = pd.DataFrame(all_dados)
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
