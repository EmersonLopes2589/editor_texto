# Editor de Texto — Editor de Notas (Tkinter)

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)]

Uma aplicação desktop leve para edição de textos e notas, desenvolvida em Python puro com Tkinter. Fornece edição básica e recursos avançados (busca/substituição, formatação de fonte e parágrafo, inserção de tabelas em texto e impressão) com interface simples.

---

## Índice

- [Demonstração](#demonstra%C3%A7%C3%A3o)
- [Funcionalidades](#funcionalidades)
- [Instalação](#instala%C3%A7%C3%A3o)
- [Uso](#uso)
- [Atalhos de teclado](#atalhos-de-teclado)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Contribuição](#contribui%C3%A7%C3%A3o)
- [Licença](#licen%C3%A7a)
- [Autor](#autor)

---

## Demonstração

> Adicione uma captura de tela em `docs/screenshot.png` ou `assets/screenshot.png`.

![Captura de tela](docs/screenshot.png)

> Se não houver imagem ainda, remova ou substitua o caminho acima.

---

## Funcionalidades

- Criar, abrir e salvar arquivos `.txt`
- Desfazer/refazer e seleção total
- Busca e substituição com opções (diferenciar maiúsculas, palavra inteira)
- Realce de ocorrências
- Diálogo de fonte (família, tamanho, negrito/itálico/sublinhado e cor)
- Formatação de parágrafos (alinhamento, recuos, espaçamento)
- Inserção de tabelas em texto (grade, simples, Markdown) com fonte monoespaçada
- Impressão para a impressora padrão do sistema
- Confirmação ao sair se houver alterações não salvas

---

## Instalação

Requisitos mínimos:

- Python 3.8+
- Tkinter (normalmente incluído na instalação padrão do Python)

Passos rápidos:

1. Clone este repositório:

```bash
git clone https://github.com/EmersonLopes2589/editor_texto.git
cd editor_texto
```

2. Execute a aplicação:

```bash
python Editor_Texto.py
# ou
python3 Editor_Texto.py
```

Se o Tkinter não estiver disponível, instale-o via gerenciador da sua distribuição ou com:

- Debian/Ubuntu: sudo apt install python3-tk
- Fedora: sudo dnf install python3-tkinter

---

## Uso

A aplicação é principalmente orientada por GUI; abra, edite e salve arquivos pelo menu "Arquivo".

- Para imprimir, use Arquivo → Imprimir... (ou `Ctrl+P`).
- Use o diálogo "Inserir tabela" para gerar tabelas em texto alinhadas corretamente.
- Alterações de fonte aplicadas à seleção usam tags internas, preservando a fonte padrão do documento.

---

## Atalhos de teclado

- Ctrl + N — Novo arquivo
- Ctrl + O — Abrir
- Ctrl + S — Salvar
- Ctrl + P — Imprimir
- Ctrl + F — Localizar
- Ctrl + H — Substituir
- Ctrl + Z — Desfazer
- Ctrl + Y — Refazer
- Ctrl + A — Selecionar tudo

---

## Estrutura do projeto

```text
editor_texto/
├── Editor_Texto.py    # Código principal (Tkinter)
├── README.md
└── docs/              # (opcional) capturas de tela e documentação
```

---

## Desenvolvimento

Dicas rápidas para desenvolvedores:

- Código principal em `Editor_Texto.py` — a aplicação é um único módulo Tkinter.
- Tags de texto: `fonte_*` para fontes aplicadas localmente, `par_*` para parágrafos, `tabela_mono` para tabelas.
- Para testar alterações rapidamente, execute `python Editor_Texto.py` em um ambiente virtual com o Python desejado.

Sugerimos formatar o código com ferramentas como `black` e adicionar linters (`flake8`) se quiser manter estilo/qualidade.

---

## Contribuição

Contribuições são bem-vindas! Abra uma issue para discutir mudanças grandes antes de enviar pull requests.

Padrões sugeridos:

- Fork → branch com nome `feat/<nome>` ou `fix/<nome>` → pull request
- Mantenha commits pequenos e descritivos
- Inclua testes ou passos para reproduzir o comportamento quando relevante

---

## Licença

No momento este repositório não inclui um arquivo de licença. Se quiser, posso adicionar uma licença permissiva (por exemplo, MIT) — diga qual prefere.

---

## Autor

Emerson Lopes



---

Se quiser, eu posso:

- adicionar badges adicionais (build / release / license),
- incluir uma captura de tela real se você enviar a imagem ou o caminho correto,
- criar um arquivo LICENSE (MIT, Apache-2.0, GPLv3, etc.),
- separar o projeto em pacotes ou adicionar um instalador.
