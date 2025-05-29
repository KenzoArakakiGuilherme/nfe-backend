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
    dados_produtos = []

    linhas_normalizadas = [normalizar(l) for l in linhas]
    try:
        idx_inicio = next(
            i for i, linha in enumerate(linhas_normalizadas)
            if "DADOS DO PRODUTO" in linha
        )
        linhas = linhas[idx_inicio + 1:]
    except StopIteration:
        return []

    i = 0
    while i < len(linhas) - 3:
        linha1 = linhas[i].strip()
        linha2 = linhas[i+1].strip()
        linha3 = linhas[i+2].strip()
        linha4 = linhas[i+3].strip()  # Código do produto

        partes_tecnicas = linha3.split()

        if len(partes_tecnicas) == 15 and sum(1 for p in partes_tecnicas if "," in p or p.replace('.', '').isdigit()) >= 10:
            descricao = f"{linha1} {linha2}".strip()
            try:
                ncm         = partes_tecnicas[0]
                cfop        = partes_tecnicas[1]
                cst         = partes_tecnicas[2]
                unid        = partes_tecnicas[3]
                qtd         = partes_tecnicas[4]
                vlr_unit    = partes_tecnicas[5]
                vlr_total   = partes_tecnicas[6]
                bc_icms     = partes_tecnicas[7]
                vlr_icms    = partes_tecnicas[8]
                vlr_ipi     = partes_tecnicas[9]
                aliq_icms   = partes_tecnicas[10]
                aliq_ipi    = partes_tecnicas[11]
                vlr_desc    = partes_tecnicas[12]
                dummy1      = partes_tecnicas[13]
                dummy2      = partes_tecnicas[14]

                codigo = linha4.strip()

                dados_produtos.append({
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
                i += 4
                continue
            except Exception:
                pass
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
