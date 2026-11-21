# Preset Studio

🌐 **Idioma:** [English](README.md) | Português (Brasil)

**Gerenciador Universal de Presets JSON & Monitor NLE em Tempo Real**

O **Preset Studio** é uma aplicação desktop leve e sem dependências externas, desenvolvida em Python e Tkinter com interface escura inspirada no **DaVinci Resolve Studio** e no **macOS**. Ele oferece edição visual nativa e pré-visualização animada em tempo real para presets do **Filmcraft** (`filmcraft.effect-presets`), além de um editor em árvore e código JSON bruto compatível com qualquer aplicativo que utilize arquivos `.json`.

---

## Funcionalidades

* **Monitor NLE & Deck de Transporte em Tempo Real**:
  * Avalia efeitos `graphic_text` e `motion` com interpolação de keyframes **Cubic Bézier** (`AutoBezier`, `ContinuousBezier`), `Linear` e `Hold`.
  * **Alças interativas na tela (Gizmos)** para arrastar **Posição**, **Escala** e **Rotação** diretamente no monitor, criando ou atualizando keyframes automaticamente no tempo atual.
  * Régua de timeline interativa com marcadores de keyframe em losango (`◆`), encaixe magnético (segure `Shift` para mover livremente), controle de velocidade (`1x` a `100x`) e modo Loop.
  * Modos de fundo (Monitor Escuro, Grade Transparente, Verde Chroma), guias de centro, *Action Safe* (95%), *Title Safe* (90%) e ponto de âncora.
  * Objetos de teste integrados (Texto de Exemplo, Retângulo, Quadrado, Círculo, Triângulo, Losango, Estrela e Bloco + Texto) para testar presets de movimento.
* **Inspetor Dinâmico**:
  * Gera controles tipados automaticamente (`Bool`, `Text`, `Float`, `Choice`, seletor de `Color`, vetores `Vec2` X/Y) com leitura ao vivo dos valores interpolados durante a reprodução.
  * **Editor de Keyframes** dedicado para ajustar tempos em segundos, valores e curvas de interpolação.
  * **Escalonamento Proporcional de Resolução**: Ao alterar `source_size`, todas as coordenadas de `position` e `anchor` (incluindo keyframes) são recalculadas proporcionalmente.
* **Três Páginas Sincronizadas**:
  1. **🎛 Inspetor & Viewer**: Edição visual estilo NLE com pré-visualização ao vivo.
  2. **🌲 Árvore JSON**: Editor hierárquico universal para qualquer estrutura JSON (adicionar, editar e remover chaves ou itens de listas).
  3. **</> Código JSON**: Edição direta do código-fonte com formatação, validação de sintaxe e sincronização instantânea com o Viewer.
* **Perfis por Aplicativo & Segurança**:
  * Gerencie pastas e modelos padrão por aplicativo (Filmcraft, OBS, EasyEffects, Godot, etc.) salvos em `~/.config/universal-preset-manager/profiles.json`.
  * Filtro de busca rápida, criação a partir de modelos, duplicação, validação de esquema e backup automático `.json.bak` a cada salvamento.

---

## Requisitos e Instalação

O Preset Studio utiliza **apenas a biblioteca padrão do Python**, dispensando instalações via `pip`.

* **Python 3.8+**
* **Tkinter** (incluso por padrão no Windows/macOS; no Ubuntu/Debian/Linux Mint, instale com `sudo apt install python3-tk`)

### Executando o Projeto

```bash
git clone [https://github.com/seu-usuario/preset-studio.git](https://github.com/seu-usuario/preset-studio.git)
cd preset-studio
python3 preset_manager.py
```

---

## Atalhos de Teclado

| Atalho | Ação |
| :--- | :--- |
| `Ctrl + S` | Salvar preset atual (atualiza o backup `.json.bak`) |
| `Ctrl + N` | Criar novo preset a partir de um modelo |
| `Espaço` | Play / Pause no Viewer |
| `←` / `→` | Avançar ou retroceder 1 quadro (30 FPS) |
| `Shift + ←` / `→` | Avançar ou retroceder 10 quadros |
| `Ctrl + ←` / `→` | Saltar para o keyframe anterior ou próximo |
| `Home` / `End` | Ir para o início ou fim da timeline |
| `Shift + Arrastar` (Timeline) | Navegar na timeline sem encaixe magnético nos keyframes |

---

## Licença

Este projeto é de código aberto e está disponível sob a [Licença MIT](LICENSE).
