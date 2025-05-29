from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os
import unicodedata

app = Flask(__name__)
CORS(app)

def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().upper()

def extrair_data_emissao(texto):
    match = re.search(r'DATA DA EMISS[AÃ]O\s*(\d{2}/\d{2}/\d{4})', texto)
    if match:
        return match.group(1)
    return ""

def extrair_dados(texto, nome_arquivo, data_emissao):
    linhas = texto.split('\n')
    dados = []
    i = 0

    while i < len(linhas):
        linha = linhas[i].strip()

        # Ignora linhas muito curtas
        if len(linha) < 10:
            i += 1
            continue

        partes = linha.split()

        # Verifica se essa linha tem pelo menos 15 colunas (linha técnica)
        if len(partes) >= 15:
            try:
                # Tenta extrair campos técnicos
                codigo      = partes[0]
                ncm         = partes[-15]
                cst         = partes[-14]
                cfop        = partes[-13]
                unid        = partes[-12]
                qtd         = partes[-11]
                vlr_unit    = partes[-10]
                vlr_desc    = partes[-9]
                vlr_total   = partes[-8]
                bc_icms     = partes[-7]
                vlr_icms    = partes[-6]
                vlr_ipi     = partes[-5]
                aliq_icms   = partes[-4]
                aliq_ipi    = partes[-3]

                # A descrição vem entre o código e os campos técnicos
                descricao_partes = partes[1: len(partes) - 15]
                descricao = " ".join(descricao_partes)

                # Verifica se a próxima linha é continuação da descrição
                if i + 1 < len(linhas):
                    prox_linha = linhas[i + 1].strip()
                    if prox_linha and not re.match(r"^\d{6,}", prox_linha):
                        descricao += " " + prox_linha.strip()
                        i += 1  # Pula essa linha adicional

                dados.append({
                    "codigo": codigo,
                    "descricao": descricao,
                    "ncm": ncm,
                    "cst": cst,
                    "cfop": cfop,
                    "unid": unid,
                    "qtd": qtd,
                    "vlr_unit": vlr_unit,
                    "vlr_desc": vlr_desc,
                    "vlr_total": vlr_total,
                    "bc_icms": bc_icms,
                    "vlr_icms": vlr_icms,
                    "vlr_ipi": vlr_ipi,
                    "aliq_icms": aliq_icms,
                    "aliq_ipi": aliq_ipi,
                    "arquivo": nome_arquivo,
                    "data_emissao": data_emissao
                })
            except Exception:
                pass

        i += 1

    return dados

@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        with pdfplumber.open(arquivo) as pdf:
            texto = "".join([page.extract_text() for page in pdf.pages])
        data_emissao = extrair_data_emissao(texto)
        nome_arquivo = arquivo.filename
        dados = extrair_dados(texto, nome_arquivo, data_emissao)
        all_dados.extend(dados)

    colunas_ordenadas = [
        "codigo", "descricao", "ncm", "cst", "cfop", "unid", "qtd",
        "vlr_unit", "vlr_desc", "vlr_total", "bc_icms", "vlr_icms",
        "vlr_ipi", "aliq_icms", "aliq_ipi", "arquivo", "data_emissao"
    ]

    if not all_dados:
        return jsonify([])

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
