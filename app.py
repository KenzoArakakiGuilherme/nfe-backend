from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
CORS(app)

def clean_number(value):
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0.0

def extrair_produtos_de_linhas(linhas, nome_arquivo, data_emissao):
    produtos = []
    buffer_linha = []
    num_campos_tecnicos = 15

    for linha in linhas:
        if not linha.strip():
            continue

        partes = linha.strip().split()
        numeros = [p for p in partes if re.fullmatch(r"[\d\.,\-]+", p)]

        if len(numeros) >= num_campos_tecnicos:
            if buffer_linha:
                codigo = buffer_linha[0]
                descricao = " ".join(buffer_linha[1:-num_campos_tecnicos])
                tecnicos = buffer_linha[-num_campos_tecnicos:]
                produtos.append({
                    "codigo": codigo,
                    "descricao": descricao.strip(),
                    "ncm": tecnicos[0],
                    "cst": tecnicos[1],
                    "cfop": tecnicos[2],
                    "unid": tecnicos[3],
                    "qtd": clean_number(tecnicos[4]),
                    "vlr_unit": clean_number(tecnicos[5]),
                    "vlr_desc": clean_number(tecnicos[6]),
                    "vlr_total": clean_number(tecnicos[7]),
                    "bc_icms": clean_number(tecnicos[8]),
                    "vlr_icms": clean_number(tecnicos[9]),
                    "vlr_ipi": clean_number(tecnicos[10]),
                    "aliq_icms": clean_number(tecnicos[11]),
                    "aliq_ipi": clean_number(tecnicos[12]),
                    "arquivo": nome_arquivo,
                    "data_emissao": data_emissao
                })
            buffer_linha = partes
        else:
            buffer_linha += partes

    if buffer_linha:
        codigo = buffer_linha[0]
        descricao = " ".join(buffer_linha[1:-num_campos_tecnicos])
        tecnicos = buffer_linha[-num_campos_tecnicos:]
        produtos.append({
            "codigo": codigo,
            "descricao": descricao.strip(),
            "ncm": tecnicos[0],
            "cst": tecnicos[1],
            "cfop": tecnicos[2],
            "unid": tecnicos[3],
            "qtd": clean_number(tecnicos[4]),
            "vlr_unit": clean_number(tecnicos[5]),
            "vlr_desc": clean_number(tecnicos[6]),
            "vlr_total": clean_number(tecnicos[7]),
            "bc_icms": clean_number(tecnicos[8]),
            "vlr_icms": clean_number(tecnicos[9]),
            "vlr_ipi": clean_number(tecnicos[10]),
            "aliq_icms": clean_number(tecnicos[11]),
            "aliq_ipi": clean_number(tecnicos[12]),
            "arquivo": nome_arquivo,
            "data_emissao": data_emissao
        })

    return produtos

def extrair_dados(texto, nome_arquivo):
    data_emissao_match = re.search(r"DATA DA EMISSÃO\s+(\d{2}/\d{2}/\d{4})", texto)
    data_emissao = data_emissao_match.group(1) if data_emissao_match else ""

    # Encontrar seção de produtos
    inicio = texto.find("DADOS DO PRODUTO/SERVIÇO")
    if inicio == -1:
        return []

    linhas = texto[inicio:].split('\n')
    return extrair_produtos_de_linhas(linhas, nome_arquivo, data_emissao)

@app.route("/upload", methods=["POST"])
def upload():
    if 'arquivos' not in request.files:
        return jsonify([])

    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        try:
            with pdfplumber.open(arquivo) as pdf:
                texto = "\n".join([page.extract_text() or "" for page in pdf.pages])
            dados = extrair_dados(texto, arquivo.filename)
            all_dados.extend(dados)
        except Exception as e:
            print(f"Erro ao processar {arquivo.filename}: {str(e)}")
            continue

    if not all_dados:
        return jsonify([])

    colunas_ordenadas = [
        'codigo', 'descricao', 'ncm', 'cst', 'cfop', 'unid', 'qtd',
        'vlr_unit', 'vlr_desc', 'vlr_total', 'bc_icms', 'vlr_icms',
        'vlr_ipi', 'aliq_icms', 'aliq_ipi', 'arquivo', 'data_emissao'
    ]

    df = pd.DataFrame(all_dados)
    for col in colunas_ordenadas:
        if col not in df.columns:
            df[col] = ""

    df = df[colunas_ordenadas]

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False)
    app.config["ULTIMO_ARQUIVO"] = temp_file.name

    return jsonify(df.to_dict(orient="records"))

@app.route("/baixar")
def baixar_excel():
    arquivo = app.config.get("ULTIMO_ARQUIVO")
    if arquivo and os.path.exists(arquivo):
        return send_file(
            arquivo,
            as_attachment=True,
            download_name="dados_nfe.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return "Nenhum arquivo gerado ainda.", 404

@app.route("/")
def home():
    return "✅ API NFe está no ar!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
