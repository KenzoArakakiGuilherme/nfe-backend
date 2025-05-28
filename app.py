from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)

# Função para extrair data da emissão
def extrair_data_emissao(texto):
    match = re.search(r'DATA DA EMISSÃO\s*(\d{2}/\d{2}/\d{4})', texto)
    if match:
        return match.group(1)
    return ""

# Função para extrair dados dos produtos, mesmo com descrição quebrada em 2 linhas
import unicodedata

def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().upper()

def extrair_dados(texto, nome_arquivo, data_emissao):
    linhas = texto.split('\n')
    dados_produtos = []

    # Normaliza as linhas para facilitar a busca da âncora
    linhas_normalizadas = [normalizar(l) for l in linhas]

    try:
        idx_inicio = next(
            i for i, linha in enumerate(linhas_normalizadas)
            if "PRODUTO" in linha and "SERVICO" in linha
        )
        linhas = linhas[idx_inicio + 1:]
    except StopIteration:
        return []  # âncora não encontrada

    buffer_descricao = ""
    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        partes = linha.split()

        if len(partes) == 15:
            try:
                aliq_ipi    = partes[-1]
                aliq_icms   = partes[-2]
                vlr_ipi     = partes[-3]
                vlr_icms    = partes[-4]
                bc_icms     = partes[-5]
                vlr_total   = partes[-6]
                vlr_desc    = partes[-7]
                vlr_unit    = partes[-8]
                qtd         = partes[-9]
                unid        = partes[-10]
                cfop        = partes[-11]
                cst         = partes[-12]
                ncm         = partes[-13]
                codigo      = partes[-14]
                descricao   = buffer_descricao.strip()

                dados_produtos.append({
                    "arquivo": nome_arquivo,
                    "data_emissao": data_emissao,
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
                    "aliq_ipi": aliq_ipi
                })

                buffer_descricao = ""  # Limpa para o próximo produto
            except Exception:
                buffer_descricao = ""  # Mesmo se der erro, limpa
        else:
            buffer_descricao += " " + linha

        i += 1

    return dados_produtos




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
