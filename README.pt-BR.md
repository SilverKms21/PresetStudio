# Preset Studio

[English](README.md) · [Português (BR)](README.pt-BR.md)

Editor e gerenciador desktop de presets JSON, escrito em Rust com [egui](https://github.com/emilk/egui).
Nasceu como uma ferramenta Python/Tkinter para **presets de efeitos do Filmcraft** e virou uma
pequena bancada para qualquer arquivo JSON: visualizador de composição com keyframes, editor em árvore,
editor bruto e visualizadores para vários formatos conhecidos.

> Interface escura inspirada no DaVinci Resolve / macOS. Inglês por padrão, com troca instantânea para português (botão EN/PT).

## Recursos

### Studio (presets Filmcraft)
- **Visualizador de composição** com gizmo de transformação: mover, escalar (cantos/bordas), rotacionar e ponto de ancoragem.
- **Caminho de movimento**: arraste os keyframes de posição direto no canvas.
- **Snap magnético** no centro e nos terços, guias de área segura, zoom, pan e fundos (escuro, xadrez, chroma verde).
- **HUD ao vivo** com posição, escala, rotação e âncora.
- **Auto-key** e botão para adicionar keyframes em todas as propriedades de transformação.
- **Timeline interativa**: navegar, arrastar keyframes (com snap por frame, `Shift` para tempo livre), **selecionar e excluir keyframes** (`Delete` / `Backspace`, menu de clique direito ou botão na barra).
- **Inspetor** agrupado em Transformação / Texto / Preenchimento e Contorno / Fundo e Sombra, com valores animados ao vivo e editor de keyframes por parâmetro (tempo, interpolação, valores).
- Preview de `graphic_text` (preenchimento, contorno, sombra, fundo, caixa alta, alinhamento) e de `motion` em formas de teste (retângulo, quadrado, círculo, triângulo, losango, estrela, texto).
- Reescala da resolução base, que também escala os keyframes de posição e âncora.

### Visualizador de formatos
Detectado automaticamente ao abrir um arquivo:

| Formato | O que você vê |
|---|---|
| **OBS Studio** (coleção de cenas ou transição avulsa) | Preview animado de Fade, Cut, Slide, Swipe, Fade to Color, Luma Wipe e Stinger; editor de configurações, duração padrão e adicionar/remover transições |
| **Lottie** | Informações da composição e timeline de camadas com cabeça de leitura |
| **GeoJSON** | Desenho de pontos, linhas e polígonos, bounding box e contagem de geometrias |
| **Transcrições** (`segments` no estilo Whisper) | Lista de segmentos com tempos, barra de timeline e contagem de palavras |
| **Qualquer outro JSON** | Estatísticas de estrutura, maiores arrays, amostras de cores hex e gráficos de arrays numéricos |

### Biblioteca e edição
- Vários **perfis** (apps), cada um com sua pasta, tipo de schema e template.
- Biblioteca de arquivos com busca, novo / duplicar / importar / renomear / excluir.
- Editor em **árvore JSON** (editar valores, adicionar/remover nós) e editor **JSON bruto** com formatar e validar.
- Backup `.bak` automático ao salvar.

## Instalação e execução

Requer **Rust 1.81+**.

```bash
git clone <url-do-seu-repositorio>
cd preset-studio
cargo run --release
```

Rodar os testes:

```bash
cargo test
```

No Linux, os diálogos de arquivo usam o `xdg-desktop-portal` (via [`rfd`](https://github.com/PolyMeilex/rfd)); garanta que um backend de portal esteja instalado (a maioria dos desktops já tem).

## Atalhos

| Ação | Atalho |
|---|---|
| Salvar / Novo preset | `Ctrl+S` / `Ctrl+N` |
| Play / pausar | `Espaço` |
| Avançar/voltar frame (×10 com `Shift`) | `←` `→` |
| Ir ao keyframe anterior / próximo | `Ctrl+←` `Ctrl+→` |
| Ir ao início / fim | `Home` / `End` |
| Excluir keyframe selecionado | `Delete` / `Backspace` |
| Zoom / pan do viewer | Roda do mouse / arrastar com botão do meio |
| Desativar snap ao arrastar | Segurar `Ctrl` |
| Rotação em passos de 15° / escala não uniforme pelo canto | Segurar `Shift` |

## Configuração

Configurações e perfis ficam em `~/.config/universal-preset-manager/`
(`profiles.json`, `settings.json`) e são compatíveis com a versão Python original.

## Estrutura do projeto

```
src/
├── main.rs        ponto de entrada
├── app.rs         perfis, biblioteca, páginas, diálogos
├── viewer.rs      viewer de composição, gizmos, timeline, renderização
├── inspector.rs   inspetor de parâmetros e editor de keyframes
├── formats.rs     visualizadores de OBS / Lottie / GeoJSON / transcrição / genérico
├── engine.rs      blending RGBA, easing Bézier, transformações 2D, hit-test
├── jsonx.rs       utilitários JSON
├── templates.rs   presets padrão embutidos (src/templates/*.json)
├── i18n.rs        textos em inglês / português
└── theme.rs       paleta e componentes de UI
```

## Limitações conhecidas

- Fontes: o egui só traz suas fontes padrão, então a família definida no preset é ignorada (negrito é simulado; itálico, sublinhado e tachado funcionam).
- Os previews do OBS aproximam as transições nativas; vídeos de stinger e imagens de luma não são carregados.
- Arquivos Lottie são inspecionados, não renderizados.
- Alguns símbolos (⏮ ◆ ◇ …) dependem dos glifos disponíveis na fonte embutida do egui.

## Licença

Adicione sua licença aqui (por exemplo, MIT).
