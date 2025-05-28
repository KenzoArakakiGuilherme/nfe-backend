from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os
import unicodedata

app = Flask(__name__)
CORS(app)  # Permite acesso externo (ex: frontend GitHub Pages)

# 🔹 Normaliza texto para remover acentos
def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().upper()

# 🔹 Extrai data de emissão da nota
def extrair_data_emissao(texto):
    match = re.search(r'DATA DA EMISS[AÃ]O\s*(\d{2}/\d{2}/\d{4})', texto)
    if match:
        return match.group(1)
    return ""

# 🔹 Extrai produtos com 15 colunas, aceita descrição em 1 ou 2 linhas
def extrair_dados(texto, nome_arquivo, data_emissao):
    linhas = texto.split('\n')
    dados_produtos = []

    # Localiza a âncora "DADOS DO PRODUTO/SERVIÇO"
    linhas_normalizadas = [normalizar(l) for l in linhas]
    try:
        idx_inicio = next(
            i for i, linha in enumerate(linhas_normalizadas)
            if "PRODUTO" in linha and "SERVICO" in linha
        )
        linhas = linhas[idx_inicio + 1:]
    except StopIteration:
        return []

    buffer_descricao = ""
    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        partes = linha.split()

        if len(partes) >= 15:
            ultimos_15 = partes[-15:]
            tem_numeros = sum(1 for p in ultimos_15 if "," in p or p.replace('.', '').isdigit())

            if tem_numeros >= 10:  # linha técnica
                try:
                    aliq_ipi    = ultimos_15[-1]
                    aliq_icms   = ultimos_15[-2]
                    vlr_ipi     = ultimos_15[-3]
                    vlr_icms    = ultimos_15[-4]
                    bc_icms     = ultimos_15[-5]
                    vlr_total   = ultimos_15[-6]
                    vlr_desc    = ultimos_15[-7]
                    vlr_unit    = ultimos_15[-8]
                    qtd         = ultimos_15[-9]
                    unid        = ultimos_15[-10]
                    cfop        = ultimos_15[-11]
                    cst         = ultimos_15[-12]
                    ncm         = ultimos_15[-13]
                    codigo      = ultimos_15[-14]

                    descricao = " ".join(partes[:-15]) if len(partes) > 15 else buffer_descricao.strip()

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

                    buffer_descricao = ""
                    i += 1
                    continue
                except Exception:
                    buffer_descricao = ""

        buffer_descricao += " " + linha
        i += 1

    return dados_produtos

# 🔹 Endpoint principal de upload
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

# 🔹 Download do último Excel gerado
@app.route("/baixar")
def baixar_excel():
    arquivo = app.config.get("ULTIMO_ARQUIVO")
    if arquivo and os.path.exists(arquivo):
        return send_file(arquivo, as_attachment=True, download_name="resultado.xlsx")
    return "Nenhum arquivo gerado ainda.", 404

# 🔹 Página inicial
@app.route("/")
def home():
    return "✅ API NFe está no ar!"

# 🔹 Configuração de porta para Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
