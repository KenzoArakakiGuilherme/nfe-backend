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
    """Converte números no formato brasileiro para float"""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0.0

def extrair_dados(texto, nome_arquivo):
    dados = []
    
    # Extrair metadados da nota
    metadados = {
        'emissor': re.search(r"IDENTIFICAÇÃO DO EMITENTE\s+(.+?)\n", texto),
        'destinatario': re.search(r"NOM[^\n]+\s+(.+?)\n", texto),
        'data_emissao': re.search(r"DATA DA EMISSÃO\s+(\d{2}/\d{2}/\d{4})", texto),
        'valor_total': re.search(r"VALOR TOTAL DA NOTA\s+([\d.,]+)", texto),
        'chave_acesso': re.search(r"CHAVE DE ACESSO\n(.+?)\n", texto, re.DOTALL)
    }
    
    metadados = {k: v.group(1).strip() if v else "" for k, v in metadados.items()}
    
    # Extrair seção de produtos
    produto_section = re.search(
        r"DADOS DO PRODUTOS?/SERVIÇO.*?\n(.+?)(?:\n\n|VALOR|$)", 
        texto, 
        re.DOTALL | re.IGNORECASE
    )
    
    if produto_section:
        produto_lines = [line.strip() for line in produto_section.group(1).split('\n') if line.strip()]
        
        current_product = None
        
        for line in produto_lines:
            # Verifica se é uma nova linha de produto (começa com código numérico)
            if re.match(r"^\d{6,}", line):
                if current_product:
                    dados.append(current_product)
                
                parts = re.split(r'\s{2,}', line)
                if len(parts) < 2:
                    continue
                    
                # Extrai código e descrição (pode estar incompleta)
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
                
                # Tenta extrair os campos numéricos no final
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
                # Continuação da descrição do produto atual
                current_product['descricao'] += " " + line
        
        if current_product:
            dados.append(current_product)
    
    # Adicionar metadados a cada produto
    for produto in dados:
        produto.update({
            'arquivo': nome_arquivo,
            'data_emissao': metadados['data_emissao'],
            'emissor': metadados['emissor'],
            'destinatario': metadados['destinatario'],
            'valor_total_nota': clean_number(metadados['valor_total']),
            'chave_acesso': metadados['chave_acesso']
        })
    
    return dados

@app.route("/upload", methods=["POST"])
def upload():
    if 'arquivos' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
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
        return jsonify({"erro": "Nenhum dado extraído dos arquivos"}), 400

    # Ordenar colunas para melhor visualização
    colunas_ordenadas = [
        'codigo', 'descricao', 'ncm', 'cst', 'cfop', 'unid', 'qtd', 
        'vlr_unit', 'vlr_desc', 'vlr_total', 'bc_icms', 'vlr_icms', 
        'vlr_ipi', 'aliq_icms', 'aliq_ipi', 'data_emissao', 'emissor',
        'destinatario', 'valor_total_nota', 'chave_acesso', 'arquivo'
    ]

    df = pd.DataFrame(all_dados)
    
    # Garantir que todas as colunas existam
    for col in colunas_ordenadas:
        if col not in df.columns:
            df[col] = ""
    
    df = df[colunas_ordenadas]
    
    # Salvar em arquivo temporário
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
    return "Nenhum arquivo gerado ainda.", 404

@app.route("/")
def home():
    return "✅ API NFe está no ar!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
