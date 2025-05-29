from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)

# Extrai a data de emissão da nota
def extrair_data_emissao(texto):
    match = re.search(r'DATA DA EMISS[AÃ]O\s*(\d{2}/\d{2}/\d{4})', texto)
    return match.group(1) if match else ""

# Função principal de extração
def extrair_dados(texto, nome_arquivo, data_emissao):
    linhas = texto.split('\n')
    dados = []
    i = 0

    while i < len(linhas):
        linha = linhas[i].strip()

        partes = linha.split()
        if len(partes) >= 16:
            try:
                # 15 últimos campos fixos
                aliq_ipi   = partes[-1]
                aliq_icms  = partes[-2]
                vlr_ipi    = partes[-3]
                vlr_icms   = partes[-4]
                bc_icms    = partes[-5]
                vlr_total  = partes[-6]
                vlr_desc   = partes[-7]
                vlr_unit   = partes[-8]
                qtd        = partes[-9]
                unid       = partes[-10]
                cfop       = partes[-11]
                cst        = partes[-12]
                ncm        = partes[-13]
                descricao  = " ".join(partes[:-15])

                # Se próxima linha parece continuação da descrição
                if i + 1 < len(linhas):
                    prox_linha = linhas[i + 1].strip()
                    if prox_linha and not re.search(r"\d{8}", prox_linha) and not prox_linha.split()[0].isdigit():
                        descricao += " " + prox_linha
                        i += 1

                # Tenta extrair o código no início
                cod_match = re.match(r"^(\d{5,})\s+(.*)", descricao)
                if cod_match:
                    codigo = cod_match.group(1)
                    descricao = cod_match.group(2)
                else:
                    codigo = ""

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
            texto = "\n".join([page.extract_text() for page in pdf.pages])
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
