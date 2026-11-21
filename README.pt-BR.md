# Preset Studio

**Um gerenciador desktop de presets JSON com visualizador de animação focado no Filmcraft.**

O Preset Studio é um aplicativo em Python/Tkinter para organizar, inspecionar, editar e visualizar presets JSON. Ele oferece suporte dedicado ao formato `filmcraft.effect-presets` e ferramentas de edição genérica para arquivos JSON de outros aplicativos.

> **Status:** versão inicial / beta. Faça cópias de segurança dos seus presets importantes antes de editá-los.

## Recursos

- **Biblioteca de presets e perfis**
  - Organize presets em perfis específicos por aplicativo.
  - Escolha uma pasta de presets para cada perfil.
  - Crie, duplique, importe, renomeie e exclua arquivos.
  - Salve um modelo próprio por perfil para criar novos presets.
- **Suporte ao Filmcraft**
  - Modelos integrados para presets `graphic_text` e `motion`.
  - Inspeção e edição de variações, efeitos e parâmetros.
  - Edição de valores com keyframes e pré-visualização de animações.
  - Validação de partes importantes da estrutura de presets do Filmcraft.
- **Visualizador de animação**
  - Pré-visualização em tempo real dos efeitos de texto e movimento suportados.
  - Timeline com trilhas separadas para parâmetros animados.
  - Controles visuais (gizmos) para mover, escalar e rotacionar objetos.
  - Ferramentas específicas para ponto de âncora e caminho de movimento.
  - Auto-Key, criação de keyframes e restauração de transformações.
  - Zoom, movimentação da área de visualização, guias de encaixe e margens de segurança.
  - Texto de exemplo e formas geométricas para testar animações.
- **Edição JSON**
  - Editor estruturado em árvore JSON.
  - Editor de código JSON com formatação e aplicação das alterações.
  - Suporte a JSON genérico de aplicativos com esquemas diferentes.
- **Segurança e fluxo de trabalho**
  - Cria um backup `.json.bak` ao salvar por cima de um preset existente.
  - Atalhos de teclado para ações comuns de edição e reprodução.
- **Idiomas**
  - Interface em inglês e português brasileiro.

## Capturas de tela

Adicione imagens ou GIFs do aplicativo aqui, por exemplo:

```markdown
![Janela principal do Preset Studio](docs/screenshots/main-window.png)
```

## Requisitos

- Linux, Windows ou macOS; Python 3.10 ou superior é recomendado.
- Tkinter / Tcl-Tk.
- A versão executada pelo código-fonte não exige bibliotecas Python de terceiros.

No Debian/Ubuntu, instale o Tkinter com:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv
```

## Executar pelo código-fonte

Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/preset-studio.git
cd preset-studio
```

Execute:

```bash
python3 main.py
```

Se sua distribuição Linux disponibilizar o Tkinter em um pacote separado, instale-o antes de iniciar o aplicativo.

## Gerar um executável Linux

O repositório inclui o script `build_linux.sh`. Ele utiliza o PyInstaller para gerar uma pasta com o executável e o ambiente necessário para executá-lo.

```bash
chmod +x build_linux.sh
./build_linux.sh
```

O resultado será criado em:

```text
dist/PresetStudio/
```

Para executar:

```bash
./dist/PresetStudio/PresetStudio
```

Se o PyInstaller ainda não estiver instalado no ambiente Python ativo, o script tentará instalá-lo. A máquina de compilação precisa ter o suporte de execução do Tkinter instalado.

Também é possível compilar manualmente:

```bash
python3 -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onedir \
  --name PresetStudio \
  main.py
```

Faça a compilação no sistema operacional de destino. Um executável Linux não funciona como executável Windows ou macOS, e o PyInstaller não garante compatibilidade com todas as distribuições Linux.

## Dados do usuário

O Preset Studio armazena as configurações de perfis e idioma em:

```text
~/.config/universal-preset-manager/
```

Os arquivos de presets continuam nas pastas configuradas nos perfis do aplicativo. A biblioteca de presets não é movida automaticamente para a pasta de configuração.

## Estrutura do projeto

```text
.
├── main.py       # Janela principal, perfis, biblioteca, inspetor e editores JSON
├── viewer.py     # Visualizador, timeline, ferramentas de transformação e caminho
├── engine.py     # Avaliação de keyframes, interpolação, geometria e transformações
├── i18n.py       # Traduções em inglês e português
├── templates.py  # Modelos Filmcraft e JSON genérico
├── theme.py      # Tema Tkinter e componentes reutilizáveis
├── README.md
├── README.pt-BR.md
└── build_linux.sh
```

## Observações sobre os formatos suportados

O visualizador especializado de animação é direcionado a presets Filmcraft com a estrutura `filmcraft.effect-presets`, especialmente os efeitos `graphic_text` e `motion`. Arquivos JSON genéricos podem ser editados pelas visualizações em árvore e código, mas seu comportamento específico não é interpretado pelo visualizador Filmcraft.

Sempre teste os presets exportados ou modificados no aplicativo de destino. O Preset Studio é uma ferramenta independente de edição e pré-visualização, não um produto oficial do Filmcraft.

## Atalhos de teclado

A interface mostra as dicas dos atalhos disponíveis. Entre as ações comuns estão:

- `Ctrl + S` — Salvar
- `Ctrl + N` — Novo preset
- `Espaço` — Reproduzir / pausar
- `Seta esquerda` / `Seta direita` — Avançar ou voltar um quadro

## Contribuição

Relatos de bugs, exemplos reproduzíveis e pull requests são bem-vindos. Ao relatar um problema, informe:

1. Sistema operacional e versão do Python.
2. Etapas para reproduzir o problema.
3. Um exemplo JSON sem dados sensíveis, se possível.
4. Qualquer traceback exibido no terminal.

## Licença

Este repositório ainda não declara uma licença. Até que uma licença seja adicionada, todos os direitos permanecem com o titular dos direitos autorais e não se deve presumir que a reutilização esteja autorizada.
