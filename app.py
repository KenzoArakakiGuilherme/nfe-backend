from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import camelot
import pandas as pd
import tempfile
import os

app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload():
    if 'arquivos' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    arquivos = request.files.getlist("arquivos")
    all_dados = []

    for arquivo in arquivos:
        nome_arquivo = arquivo.filename
        try:
            # Salvar temporariamente o PDF para leitura pelo Camelot
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            arquivo.save(temp_pdf.name)

            # Extrair tabelas com Camelot
            tabelas = camelot.read_pdf(temp_pdf.name, pages='all', strip_text='\n')

            for tabela in tabelas:
                df = tabela.df

                # Identificar a linha de cabeçalho corretamente
                cabecalho_idx = df[df.apply(lambda x: 'DESCRIÇÃO' in ''.join(x), axis=1)].index
                if not cabecalho_idx.empty:
                    header_row = cabecalho_idx[0]
                    df.columns = df.iloc[header_row]
                    df = df.iloc[header_row + 1:]

                    # Adicionar nome do arquivo
                    df['arquivo'] = nome_arquivo
                    all_dados.append(df)

        except Exception as e:
            print(f"Erro ao processar {nome_arquivo}: {str(e)}")
            continue

    if not all_dados:
        return jsonify([])

    df_final = pd.concat(all_dados, ignore_index=True)

    # Salvar arquivo Excel temporariamente
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df_final.to_excel(temp_file.name, index=False)
    app.config["ULTIMO_ARQUIVO"] = temp_file.name

    return df_final.to_json(orient="records", force_ascii=False)

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
    return "✅ API NFe com Camelot está ativa!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

