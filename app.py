from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)  # ✅ Permite acesso do frontend (evita erro de CORS)

# Função para extrair dados dos PDFs
def extrair_dados(texto):
    linhas = texto.split('\n')
    dados_produtos = []

    for linha in linhas:
        if re.match(r"^\d{6,}", linha) and "," in linha:
            partes = linha.strip().split()
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
                codigo      = partes[0]
                descricao   = " ".join(partes[1:-13])

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
                    "aliq_ipi": aliq_ipi
                })
            except:
                continue
    return dados_produtos

# ✅ Rota para upload e extração dos dados (retorna JSON)
@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        with pdfplumber.open(arquivo) as pdf:
            texto = "".join([page.extract_text() for page in pdf.pages])
        dados = extrair_dados(texto)
        all_dados.extend(dados)

    # Salva Excel temporariamente para uso posterior
    df = pd.DataFrame(all_dados)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False)
    app.config["ULTIMO_ARQUIVO"] = temp_file.name

    return jsonify(all_dados)

# ✅ Rota para download manual do Excel
@app.route("/baixar")
def baixar_excel():
    arquivo = app.config.get("ULTIMO_ARQUIVO")
    if arquivo and os.path.exists(arquivo):
        return send_file(arquivo, as_attachment=True, download_name="resultado.xlsx")
    return "Nenhum arquivo gerado ainda.", 404

# Página inicial simples
@app.route("/")
def home():
    return "✅ API NFe está no ar!"

# ⚙️ Configuração do host/porta para o Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
