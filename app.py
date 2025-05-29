<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <title>Leitor de Notas Fiscais</title>
</head>
<body>
  <h2>Upload de Notas Fiscais em PDF</h2>
  <form id="uploadForm">
    <input type="file" name="arquivos" multiple accept=".pdf" required />
    <button type="submit">Enviar e Visualizar Dados</button>
  </form>

  <p id="status"></p>
  <button id="baixarExcel" style="display:none;">Baixar Excel</button>

  <div id="tabelaResultado"></div>

  <script>
    const form = document.getElementById("uploadForm");
    const status = document.getElementById("status");
    const tabela = document.getElementById("tabelaResultado");
    const botaoBaixar = document.getElementById("baixarExcel");

    form.onsubmit = async (e) => {
      e.preventDefault();
      status.innerText = "⏳ Processando PDFs...";
      tabela.innerHTML = "";
      botaoBaixar.style.display = "none";

      const formData = new FormData(form);

      try {
        const response = await fetch("https://nfe-backend.onrender.com/upload", {
          method: "POST",
          body: formData
        });

        const dados = await response.json();

        if (!dados.length) {
          status.innerText = "⚠️ Nenhum produto encontrado.";
          return;
        }

        // Construir tabela
        let html = "<table border='1'><tr>";
        for (const key of Object.keys(dados[0])) {
          html += `<th>${key}</th>`;
        }
        html += "</tr>";
        for (const item of dados) {
          html += "<tr>";
          for (const valor of Object.values(item)) {
            html += `<td>${valor}</td>`;
          }
          html += "</tr>";
        }
        html += "</table>";

        tabela.innerHTML = html;
        botaoBaixar.style.display = "inline";
        status.innerText = "✅ Dados extraídos com sucesso!";
      } catch (error) {
        console.error(error);
        status.innerText = "❌ Erro ao conectar ao servidor.";
      }
    };

    botaoBaixar.onclick = () => {
      window.open("https://nfe-backend.onrender.com/baixar", "_blank");
    };
  </script>
</body>
</html>
