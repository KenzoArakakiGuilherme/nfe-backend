from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import tempfile
import os

app = Flask(__name__)
# Configuração mais segura do CORS
CORS(app, resources={
    r"/upload": {"origins": ["*"], "methods": ["POST"], "allow_headers": ["Content-Type"]},
    r"/baixar": {"origins": ["*"]}
})

def clean_number(value):
    """Converte números no formato brasileiro para float"""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0.0

def extrair_dados(texto, nome_arquivo):
    dados = []
    
    try:
        # Extrair metadados
        metadados = {
            'emissor': re.search(r"IDENTIFICAÇÃO DO EMITENTE\s+(.+?)\n", texto),
            'destinatario': re.search(r"NOM[^\n]+\s+(.+?)\n", texto),
            'data_emissao': re.search(r"DATA DA EMISSÃO\s+(\d{2}/\d{2}/\d{4})", texto),
            'valor_total': re.search(r"VALOR TOTAL DA NOTA\s+([\d.,]+)", texto),
            'chave_acesso': re.search(r"CHAVE DE ACESSO\n(.+?)\n", texto, re.DOTALL)
        }
        
        metadados = {k: v.group(1).strip() if v else "" for k, v in metadados.items()}

        # Extrair produtos
        produto_section = re.search(
            r"DADOS DO PRODUTOS?/SERVIÇO.*?\n(.+?)(?:\n\n|VALOR|$)", 
            texto, 
            re.DOTALL | re.IGNORECASE
        )
        
        if produto_section:
            produto_lines = [line.strip() for line in produto_section.group(1).split('\n') if line.strip()]
            
            current_product = None
            
            for line in produto_lines:
                if re.match(r"^\d{6,}", line):
                    if current_product:
                        dados.append(current_product)
                    
                    parts = re.split(r'\s{2,}', line)
                    if len(parts) < 2:
                        continue
                        
                    current_product = {
                        'codigo': parts[0],
                        'descricao': parts[1],
                        'ncm': '',
                        'cst': '',
                        'cfop': '',
                        'unid': '',
                        'qtd': '',
                        'vlr_unit': '',
                        'vlr_desc': '',
                        'vlr_total': '',
                        'bc_icms': '',
                        'vlr_icms': '',
                        'vlr_ipi': '',
                        'aliq_icms': '',
                        'aliq_ipi': ''
                    }
                    
                    numeric_fields = re.findall(r"(-?\d[\d.,]*)", line)
                    if len(numeric_fields) >= 13:
                        fields = numeric_fields[-13:]
                        current_product.update({
                            'ncm': fields[0],
                            'cst': fields[1],
                            'cfop': fields[2],
                            'unid': fields[3],
                            'qtd': clean_number(fields[4]),
                            'vlr_unit': clean_number(fields[5]),
                            'vlr_desc': clean_number(fields[6]),
                            'vlr_total': clean_number(fields[7]),
                            'bc_icms': clean_number(fields[8]),
                            'vlr_icms': clean_number(fields[9]),
                            'vlr_ipi': clean_number(fields[10]),
                            'aliq_icms': clean_number(fields[11]),
                            'aliq_ipi': clean_number(fields[12])
                        })
                elif current_product:
                    current_product['descricao'] += " " + line
            
            if current_product:
                dados.append(current_product)
        
        # Adicionar metadados
        for produto in dados:
            produto.update({
                'arquivo': nome_arquivo,
                'data_emissao': metadados['data_emissao'],
                'emissor': metadados['emissor'],
                'destinatario': metadados['destinatario'],
                'valor_total_nota': clean_number(metadados['valor_total']),
                'chave_acesso': metadados['chave_acesso']
            })
            
    except Exception as e:
        print(f"Erro ao extrair dados do arquivo {nome_arquivo}: {str(e)}")
    
    return dados

@app.route("/upload", methods=["POST"])
def upload():
    # Verifica se o cabeçalho Content-Type é multipart/form-data
    if 'Content-Type' not in request.headers or 'multipart/form-data' not in request.headers['Content-Type']:
        return jsonify({"erro": "Content-Type deve ser multipart/form-data"}), 400
        
    if 'arquivos' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
    arquivos = request.files.getlist("arquivos")
    if not arquivos or not arquivos[0].filename:
        return jsonify({"erro": "Nenhum arquivo válido enviado"}), 400
    
    all_dados = []

    for arquivo in arquivos:
        try:
            # Verifica se é um PDF
            if not arquivo.filename.lower().endswith('.pdf'):
                continue
                
            with pdfplumber.open(arquivo.stream) as pdf:
                texto = "\n".join([page.extract_text() or "" for page in pdf.pages])
                dados = extrair_dados(texto, arquivo.filename)
                all_dados.extend(dados)
        except Exception as e:
            print(f"Erro ao processar {arquivo.filename}: {str(e)}")
            continue

    if not all_dados:
        return jsonify({"erro": "Nenhum dado extraído dos arquivos"}), 400

    colunas_ordenadas = [
        'codigo', 'descricao', 'ncm', 'cst', 'cfop', 'unid', 'qtd', 
        'vlr_unit', 'vlr_desc', 'vlr_total', 'bc_icms', 'vlr_icms', 
        'vlr_ipi', 'aliq_icms', 'aliq_ipi', 'data_emissao', 'emissor',
        'destinatario', 'valor_total_nota', 'chave_acesso', 'arquivo'
    ]

    df = pd.DataFrame(all_dados)
    for col in colunas_ordenadas:
        if col not in df.columns:
            df[col] = ""
    df = df[colunas_ordenadas]
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False)
    app.config["ULTIMO_ARQUIVO"] = temp_file.name

    return jsonify(all_dados)

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
    return jsonify({"erro": "Nenhum arquivo gerado ainda"}), 404

@app.route("/")
def home():
    return "✅ API NFe está no ar!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
