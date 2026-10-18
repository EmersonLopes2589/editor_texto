import os
import re
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont


# JANELA PRINCIPAL E ÁREA DE TEXTO
class EditorNotas(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Editor de Notas")
        self.geometry("820x560")

        self.caminho_atual = None
        self.janela_localizar = None
        self.fontes_criadas = {}          # nome_tag -> tkfont.Font (mantém referência viva)
        self.contador_paragrafo = 0
        self.fonte_padrao = tkfont.Font(family="Segoe UI", size=11)
        self.fonte_mono = tkfont.Font(family="Consolas", size=11)

        quadro = tk.Frame(self)
        quadro.pack(expand=True, fill=tk.BOTH)

        barra_rolagem = tk.Scrollbar(quadro)
        barra_rolagem.pack(side=tk.RIGHT, fill=tk.Y)

        self.area_texto = tk.Text(
            quadro,
            wrap=tk.WORD,
            undo=True,
            font=self.fonte_padrao,
            yscrollcommand=barra_rolagem.set,
            padx=8,
            pady=6,
        )
        self.area_texto.pack(expand=True, fill=tk.BOTH)
        barra_rolagem.config(command=self.area_texto.yview)

        self.area_texto.tag_configure("localizado", background="#fff176")
        self.area_texto.tag_configure("tabela_mono", font=self.fonte_mono)

        self.criar_menu()
        self.criar_atalhos()
        self.protocol("WM_DELETE_WINDOW", self.sair)

    # MENUS (ARQUIVO E EDITAR)
    def criar_menu(self):
        menubar = tk.Menu(self)

        # ── Arquivo ──
        menu_arquivo = tk.Menu(menubar, tearoff=0)
        menu_arquivo.add_command(label="Novo", accelerator="Ctrl+N", command=self.novo_arquivo)
        menu_arquivo.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.abrir_arquivo)
        menu_arquivo.add_command(label="Salvar", accelerator="Ctrl+S", command=self.salvar_arquivo)
        menu_arquivo.add_command(label="Salvar como...", command=self.salvar_como)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Imprimir...", accelerator="Ctrl+P", command=self.imprimir)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", command=self.sair)
        menubar.add_cascade(label="Arquivo", menu=menu_arquivo)

        # ── Editar ──
        menu_editar = tk.Menu(menubar, tearoff=0)
        menu_editar.add_command(label="Desfazer", accelerator="Ctrl+Z", command=self.desfazer)
        menu_editar.add_command(label="Refazer", accelerator="Ctrl+Y", command=self.refazer)
        menu_editar.add_separator()
        menu_editar.add_command(
            label="Recortar", accelerator="Ctrl+X",
            command=lambda: self.area_texto.event_generate("<<Cut>>"))
        menu_editar.add_command(
            label="Copiar", accelerator="Ctrl+C",
            command=lambda: self.area_texto.event_generate("<<Copy>>"))
        menu_editar.add_command(
            label="Colar", accelerator="Ctrl+V",
            command=lambda: self.area_texto.event_generate("<<Paste>>"))
        menu_editar.add_command(
            label="Selecionar tudo", accelerator="Ctrl+A", command=self.selecionar_tudo)
        menu_editar.add_separator()
        menu_editar.add_command(
            label="Localizar...", accelerator="Ctrl+F",
            command=lambda: self.abrir_localizar(substituir=False))
        menu_editar.add_command(
            label="Substituir...", accelerator="Ctrl+H",
            command=lambda: self.abrir_localizar(substituir=True))
        menu_editar.add_separator()
        menu_editar.add_command(label="Fonte...", command=self.abrir_fonte)
        menu_editar.add_command(label="Parágrafo...", command=self.abrir_paragrafo)
        menu_editar.add_separator()
        menu_editar.add_command(label="Inserir tabela...", command=self.abrir_inserir_tabela)
        menubar.add_cascade(label="Editar", menu=menu_editar)

        self.config(menu=menubar)

    # ATALHOS DE TECLADO
    def criar_atalhos(self):
        self.bind_all("<Control-n>", lambda e: self.novo_arquivo())
        self.bind_all("<Control-o>", lambda e: self.abrir_arquivo())
        self.bind_all("<Control-s>", lambda e: self.salvar_arquivo())
        self.bind_all("<Control-p>", lambda e: self.imprimir())
        self.bind_all("<Control-f>", lambda e: self.abrir_localizar(substituir=False))
        self.bind_all("<Control-h>", lambda e: self.abrir_localizar(substituir=True))
        self.bind_all("<Control-y>", lambda e: self.refazer())
        self.area_texto.bind("<Control-a>", lambda e: self.selecionar_tudo())

    # ── AUXILIARES DE EDIÇÃO ──
    def desfazer(self):
        try:
            self.area_texto.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def refazer(self):
        try:
            self.area_texto.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def selecionar_tudo(self):
        self.area_texto.tag_add(tk.SEL, "1.0", "end-1c")
        self.area_texto.mark_set(tk.INSERT, "1.0")
        self.area_texto.see(tk.INSERT)
        return "break"

    def intervalo_selecao(self):
        """Retorna (inicio, fim) da seleção ou None se não houver texto selecionado."""
        try:
            return self.area_texto.index(tk.SEL_FIRST), self.area_texto.index(tk.SEL_LAST)
        except tk.TclError:
            return None

    def confirmar_descarte(self):
        """Pergunta ao usuário se deseja salvar alterações não salvas. Retorna False para cancelar."""
        if not self.area_texto.edit_modified():
            return True
        resposta = messagebox.askyesnocancel(
            "Editor de Notas", "O texto foi alterado. Deseja salvar antes de continuar?")
        if resposta is None:
            return False
        if resposta:
            return self.salvar_arquivo()
        return True

    def atualizar_titulo(self):
        nome = os.path.basename(self.caminho_atual) if self.caminho_atual else "Sem título"
        self.title(f"{nome} - Editor de Notas")

    # NOVO ARQUIVO
    def novo_arquivo(self):
        if not self.confirmar_descarte():
            return
        self.area_texto.delete("1.0", tk.END)
        self.area_texto.edit_reset()
        self.area_texto.edit_modified(False)
        self.caminho_atual = None
        self.atualizar_titulo()

    # ABRIR ARQUIVO DE TEXTO
    def abrir_arquivo(self):
        if not self.confirmar_descarte():
            return
        caminho = filedialog.askopenfilename(
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                conteudo = arquivo.read()
            self.area_texto.delete("1.0", tk.END)
            self.area_texto.insert(tk.END, conteudo)
            self.area_texto.edit_reset()
            self.area_texto.edit_modified(False)
            self.caminho_atual = caminho
            self.atualizar_titulo()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir: {e}")

    # SALVAR ARQUIVO DE TEXTO
    def salvar_arquivo(self):
        if not self.caminho_atual:
            return self.salvar_como()
        return self._gravar(self.caminho_atual)

    def salvar_como(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos", "*.*")])
        if not caminho:
            return False
        return self._gravar(caminho)

    def _gravar(self, caminho):
        try:
            conteudo = self.area_texto.get("1.0", "end-1c")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write(conteudo)
            self.caminho_atual = caminho
            self.area_texto.edit_modified(False)
            self.atualizar_titulo()
            return True
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")
            return False

    # IMPRIMIR (envia o texto para a impressora padrão do sistema)
    def imprimir(self):
        conteudo = self.area_texto.get("1.0", "end-1c")
        if not conteudo.strip():
            messagebox.showinfo("Imprimir", "Não há texto para imprimir.")
            return
        if not messagebox.askyesno(
                "Imprimir", "Enviar o texto para a impressora padrão do sistema?"):
            return

        nome_base = os.path.basename(self.caminho_atual) if self.caminho_atual else "Sem título"
        try:
            # Arquivo temporário .txt (o Windows imprime .txt via Bloco de Notas/associação padrão)
            with tempfile.NamedTemporaryFile(
                    "w", suffix=".txt", prefix="editor_notas_",
                    delete=False, encoding="utf-8-sig") as temporario:
                temporario.write(f"{nome_base}\n{'=' * len(nome_base)}\n\n")
                temporario.write(conteudo)
                caminho_temp = temporario.name

            if sys.platform.startswith("win"):
                os.startfile(caminho_temp, "print")
            elif sys.platform == "darwin":
                subprocess.run(["lpr", caminho_temp], check=True)
            else:
                subprocess.run(["lp", caminho_temp], check=True)
        except Exception as e:
            messagebox.showerror("Imprimir", f"Não foi possível imprimir: {e}")

    # SAIR COM CONFIRMAÇÃO
    def sair(self):
        if self.confirmar_descarte():
            self.destroy()

    # ════════════════════════════════════════════════════════════════
    # EDITAR ▸ LOCALIZAR E SUBSTITUIR
    # ════════════════════════════════════════════════════════════════
    def abrir_localizar(self, substituir=False):
        if self.janela_localizar is not None and self.janela_localizar.winfo_exists():
            self.janela_localizar.lift()
            self.janela_localizar.focus_set()
            return

        janela = tk.Toplevel(self)
        janela.title("Substituir" if substituir else "Localizar")
        janela.transient(self)
        janela.resizable(False, False)
        self.janela_localizar = janela

        self.var_localizar = tk.StringVar()
        self.var_substituir = tk.StringVar()
        self.var_maiusculas = tk.BooleanVar(value=False)
        self.var_palavra_inteira = tk.BooleanVar(value=False)
        self.var_status_busca = tk.StringVar()

        intervalo = self.intervalo_selecao()
        if intervalo:
            selecao = self.area_texto.get(*intervalo)
            if "\n" not in selecao:
                self.var_localizar.set(selecao)

        corpo = ttk.Frame(janela, padding=12)
        corpo.pack(fill=tk.BOTH, expand=True)

        ttk.Label(corpo, text="Localizar:").grid(row=0, column=0, sticky="w", pady=3)
        entrada_busca = ttk.Entry(corpo, textvariable=self.var_localizar, width=36)
        entrada_busca.grid(row=0, column=1, columnspan=2, sticky="we", pady=3, padx=(6, 0))

        ttk.Label(corpo, text="Substituir por:").grid(row=1, column=0, sticky="w", pady=3)
        entrada_subst = ttk.Entry(corpo, textvariable=self.var_substituir, width=36)
        entrada_subst.grid(row=1, column=1, columnspan=2, sticky="we", pady=3, padx=(6, 0))

        opcoes = ttk.Frame(corpo)
        opcoes.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 2))
        ttk.Checkbutton(opcoes, text="Diferenciar maiúsculas/minúsculas",
                        variable=self.var_maiusculas).pack(side=tk.LEFT)
        ttk.Checkbutton(opcoes, text="Palavra inteira",
                        variable=self.var_palavra_inteira).pack(side=tk.LEFT, padx=(12, 0))

        botoes = ttk.Frame(corpo)
        botoes.grid(row=0, column=3, rowspan=4, sticky="n", padx=(12, 0))
        ttk.Button(botoes, text="Localizar próxima", width=18,
                   command=self.localizar_proxima).pack(pady=2)
        ttk.Button(botoes, text="Localizar anterior", width=18,
                   command=lambda: self.localizar_proxima(voltar=True)).pack(pady=2)
        ttk.Button(botoes, text="Realçar todas", width=18,
                   command=self.realcar_todas).pack(pady=2)
        ttk.Button(botoes, text="Substituir", width=18,
                   command=self.substituir_atual).pack(pady=2)
        ttk.Button(botoes, text="Substituir todas", width=18,
                   command=self.substituir_todas).pack(pady=2)
        ttk.Button(botoes, text="Fechar", width=18,
                   command=self.fechar_localizar).pack(pady=(10, 2))

        ttk.Label(corpo, textvariable=self.var_status_busca, foreground="#555").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))

        entrada_busca.bind("<Return>", lambda e: self.localizar_proxima())
        entrada_busca.bind("<Shift-Return>", lambda e: self.localizar_proxima(voltar=True))
        janela.bind("<Escape>", lambda e: self.fechar_localizar())
        janela.protocol("WM_DELETE_WINDOW", self.fechar_localizar)

        # Posiciona próximo ao canto superior direito do editor
        self.update_idletasks()
        x = self.winfo_rootx() + self.winfo_width() - 560
        y = self.winfo_rooty() + 40
        janela.geometry(f"+{max(0, x)}+{max(0, y)}")

        (entrada_subst if substituir and self.var_localizar.get() else entrada_busca).focus_set()
        entrada_busca.select_range(0, tk.END)

    def fechar_localizar(self):
        self.area_texto.tag_remove("localizado", "1.0", tk.END)
        if self.janela_localizar is not None and self.janela_localizar.winfo_exists():
            self.janela_localizar.destroy()
        self.janela_localizar = None
        self.area_texto.focus_set()

    def _padrao_busca(self):
        """Monta o padrão (regex se 'palavra inteira') e as opções para o Text.search."""
        termo = self.var_localizar.get()
        if not termo:
            return None, {}
        nocase = not self.var_maiusculas.get()
        if self.var_palavra_inteira.get():
            return rf"\m{re.escape(termo)}\M", {"regexp": True, "nocase": nocase}
        return termo, {"exact": True, "nocase": nocase}

    def localizar_proxima(self, voltar=False):
        padrao, opcoes = self._padrao_busca()
        if padrao is None:
            self.var_status_busca.set("Digite um texto para localizar.")
            return False

        tamanho = tk.IntVar()
        if voltar:
            inicio = self.area_texto.index(tk.SEL_FIRST) if self.intervalo_selecao() else tk.INSERT
            posicao = self.area_texto.search(
                padrao, inicio, stopindex="1.0", backwards=True, count=tamanho, **opcoes)
            if not posicao:
                posicao = self.area_texto.search(
                    padrao, tk.END, stopindex="1.0", backwards=True, count=tamanho, **opcoes)
        else:
            inicio = self.area_texto.index(tk.SEL_LAST) if self.intervalo_selecao() else tk.INSERT
            posicao = self.area_texto.search(
                padrao, inicio, stopindex=tk.END, count=tamanho, **opcoes)
            if not posicao:
                posicao = self.area_texto.search(
                    padrao, "1.0", stopindex=tk.END, count=tamanho, **opcoes)

        if not posicao or tamanho.get() == 0:
            self.var_status_busca.set(f'"{self.var_localizar.get()}" não foi encontrado.')
            self.bell()
            return False

        fim = f"{posicao}+{tamanho.get()}c"
        self.area_texto.tag_remove(tk.SEL, "1.0", tk.END)
        self.area_texto.tag_add(tk.SEL, posicao, fim)
        self.area_texto.mark_set(tk.INSERT, posicao if voltar else fim)
        self.area_texto.see(posicao)
        linha, coluna = posicao.split(".")
        self.var_status_busca.set(f"Encontrado na linha {linha}, coluna {int(coluna) + 1}.")
        return True

    def _iterar_ocorrencias(self, padrao, opcoes):
        """Gera (inicio, fim) de todas as ocorrências, do início ao fim do texto."""
        tamanho = tk.IntVar()
        posicao = "1.0"
        while True:
            posicao = self.area_texto.search(
                padrao, posicao, stopindex=tk.END, count=tamanho, **opcoes)
            if not posicao or tamanho.get() == 0:
                break
            fim = f"{posicao}+{tamanho.get()}c"
            yield posicao, fim
            posicao = fim

    def realcar_todas(self):
        self.area_texto.tag_remove("localizado", "1.0", tk.END)
        padrao, opcoes = self._padrao_busca()
        if padrao is None:
            return
        total = 0
        for inicio, fim in self._iterar_ocorrencias(padrao, opcoes):
            self.area_texto.tag_add("localizado", inicio, fim)
            total += 1
        self.area_texto.tag_raise("localizado")
        self.var_status_busca.set(f"{total} ocorrência(s) realçada(s).")

    def substituir_atual(self):
        padrao, opcoes = self._padrao_busca()
        if padrao is None:
            return
        intervalo = self.intervalo_selecao()
        if intervalo:
            selecionado = self.area_texto.get(*intervalo)
            termo = self.var_localizar.get()
            igual = (selecionado == termo if self.var_maiusculas.get()
                     else selecionado.lower() == termo.lower())
            if igual:
                novo = self.var_substituir.get()
                self.area_texto.delete(*intervalo)
                self.area_texto.insert(intervalo[0], novo)
                self.area_texto.mark_set(tk.INSERT, f"{intervalo[0]}+{len(novo)}c")
        self.localizar_proxima()

    def substituir_todas(self):
        padrao, opcoes = self._padrao_busca()
        if padrao is None:
            return
        novo = self.var_substituir.get()
        tamanho = tk.IntVar()
        posicao = "1.0"
        total = 0
        self.area_texto.edit_separator()
        while True:
            posicao = self.area_texto.search(
                padrao, posicao, stopindex=tk.END, count=tamanho, **opcoes)
            if not posicao or tamanho.get() == 0:
                break
            self.area_texto.delete(posicao, f"{posicao}+{tamanho.get()}c")
            self.area_texto.insert(posicao, novo)
            posicao = f"{posicao}+{len(novo)}c"
            total += 1
        self.area_texto.edit_separator()
        self.area_texto.tag_remove("localizado", "1.0", tk.END)
        self.var_status_busca.set(f"{total} substituição(ões) realizada(s).")

    # ════════════════════════════════════════════════════════════════
    # EDITAR ▸ FONTE
    # ════════════════════════════════════════════════════════════════
    def _criar_dialogo(self, titulo):
        janela = tk.Toplevel(self)
        janela.title(titulo)
        janela.transient(self)
        janela.resizable(False, False)
        janela.grab_set()
        corpo = ttk.Frame(janela, padding=12)
        corpo.pack(fill=tk.BOTH, expand=True)
        janela.bind("<Escape>", lambda e: janela.destroy())
        self.update_idletasks()
        janela.geometry(f"+{self.winfo_rootx() + 120}+{self.winfo_rooty() + 80}")
        return janela, corpo

    def abrir_fonte(self):
        janela, corpo = self._criar_dialogo("Fonte")

        fonte_atual = self.fonte_padrao.actual()
        var_familia = tk.StringVar(value=fonte_atual["family"])
        var_tamanho = tk.IntVar(value=fonte_atual["size"])
        var_negrito = tk.BooleanVar(value=fonte_atual["weight"] == "bold")
        var_italico = tk.BooleanVar(value=fonte_atual["slant"] == "italic")
        var_sublinhado = tk.BooleanVar(value=bool(fonte_atual["underline"]))
        var_cor = tk.StringVar(value=str(self.area_texto.cget("fg")))
        var_escopo = tk.StringVar(value="selecao" if self.intervalo_selecao() else "tudo")

        familias = sorted(set(tkfont.families()), key=str.lower)

        ttk.Label(corpo, text="Fonte:").grid(row=0, column=0, sticky="w")
        ttk.Label(corpo, text="Tamanho:").grid(row=0, column=1, sticky="w", padx=(10, 0))

        lista = tk.Listbox(corpo, height=12, width=34, exportselection=False)
        for familia in familias:
            lista.insert(tk.END, familia)
        lista.grid(row=1, column=0, sticky="nsew")
        barra = ttk.Scrollbar(corpo, command=lista.yview)
        barra.grid(row=1, column=0, sticky="nse")
        lista.config(yscrollcommand=barra.set)
        if var_familia.get() in familias:
            indice = familias.index(var_familia.get())
            lista.selection_set(indice)
            lista.see(indice)

        tamanhos = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72]
        ttk.Spinbox(corpo, from_=6, to=120, textvariable=var_tamanho, values=tamanhos,
                    width=6).grid(row=1, column=1, sticky="nw", padx=(10, 0))

        estilos = ttk.LabelFrame(corpo, text="Estilo", padding=6)
        estilos.grid(row=1, column=2, sticky="nw", padx=(10, 0))
        ttk.Checkbutton(estilos, text="Negrito", variable=var_negrito).pack(anchor="w")
        ttk.Checkbutton(estilos, text="Itálico", variable=var_italico).pack(anchor="w")
        ttk.Checkbutton(estilos, text="Sublinhado", variable=var_sublinhado).pack(anchor="w")

        quadro_cor = ttk.Frame(estilos)
        quadro_cor.pack(anchor="w", pady=(6, 0))
        amostra_cor = tk.Label(quadro_cor, width=3, bg=var_cor.get(), relief="sunken")

        def escolher_cor():
            from tkinter import colorchooser
            cor = colorchooser.askcolor(color=var_cor.get(), parent=janela, title="Cor do texto")
            if cor and cor[1]:
                var_cor.set(cor[1])
                amostra_cor.configure(bg=cor[1])
                atualizar_previa()

        ttk.Button(quadro_cor, text="Cor...", command=escolher_cor, width=8).pack(side=tk.LEFT)
        amostra_cor.pack(side=tk.LEFT, padx=(6, 0))

        escopo = ttk.LabelFrame(corpo, text="Aplicar em", padding=6)
        escopo.grid(row=2, column=0, columnspan=3, sticky="we", pady=(10, 0))
        ttk.Radiobutton(escopo, text="Texto selecionado", value="selecao",
                        variable=var_escopo).pack(side=tk.LEFT)
        ttk.Radiobutton(escopo, text="Documento inteiro (fonte padrão)", value="tudo",
                        variable=var_escopo).pack(side=tk.LEFT, padx=(14, 0))

        fonte_previa = tkfont.Font(font=self.fonte_padrao)
        previa = tk.Label(corpo, text="AaBbCc – O rato roeu a roupa do rei de Roma 0123",
                          font=fonte_previa, anchor="w", relief="groove", padx=8, pady=10)
        previa.grid(row=3, column=0, columnspan=3, sticky="we", pady=(10, 0))

        def fonte_escolhida():
            selecao = lista.curselection()
            familia = lista.get(selecao[0]) if selecao else var_familia.get()
            try:
                tamanho = max(1, int(var_tamanho.get()))
            except (tk.TclError, ValueError):
                tamanho = 11
            return dict(
                family=familia,
                size=tamanho,
                weight="bold" if var_negrito.get() else "normal",
                slant="italic" if var_italico.get() else "roman",
                underline=var_sublinhado.get(),
            )

        def atualizar_previa(*_):
            fonte_previa.configure(**fonte_escolhida())
            previa.configure(fg=var_cor.get())

        lista.bind("<<ListboxSelect>>", atualizar_previa)
        for variavel in (var_tamanho, var_negrito, var_italico, var_sublinhado):
            variavel.trace_add("write", atualizar_previa)
        atualizar_previa()

        def aplicar():
            if self.aplicar_fonte(fonte_escolhida(), var_cor.get(), var_escopo.get(), janela):
                janela.destroy()

        botoes = ttk.Frame(corpo)
        botoes.grid(row=4, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(botoes, text="Cancelar", command=janela.destroy).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="OK", command=aplicar).pack(side=tk.RIGHT, padx=(0, 6))
        janela.bind("<Return>", lambda e: aplicar())

    def aplicar_fonte(self, config, cor, escopo, pai=None):
        """Aplica a fonte ao documento (fonte padrão) ou à seleção (via tag)."""
        if escopo == "tudo":
            self.fonte_padrao.configure(**config)
            self.area_texto.configure(fg=cor)
            return True

        intervalo = self.intervalo_selecao()
        if not intervalo:
            messagebox.showinfo("Fonte", "Selecione um trecho do texto primeiro.",
                                parent=pai or self)
            return False

        nome_tag = f"fonte_{len(self.fontes_criadas) + 1}"
        fonte = tkfont.Font(**config)
        self.fontes_criadas[nome_tag] = fonte
        self.area_texto.tag_configure(nome_tag, font=fonte, foreground=cor)
        # remove fontes anteriores do trecho para não acumular tags conflitantes
        for tag in self.area_texto.tag_names():
            if tag.startswith("fonte_") and tag != nome_tag:
                self.area_texto.tag_remove(tag, *intervalo)
        self.area_texto.tag_add(nome_tag, *intervalo)
        return True

    # ════════════════════════════════════════════════════════════════
    # EDITAR ▸ PARÁGRAFO
    # ════════════════════════════════════════════════════════════════
    def linhas_alvo(self):
        """Retorna (inicio, fim) cobrindo as linhas inteiras da seleção ou do cursor."""
        intervalo = self.intervalo_selecao()
        if intervalo:
            inicio, fim = intervalo
            # se a seleção termina exatamente no começo de uma linha, não inclui essa linha
            if self.area_texto.compare(fim, "==", f"{fim} linestart") and \
                    self.area_texto.compare(fim, ">", inicio):
                fim = f"{fim}-1c"
        else:
            inicio = fim = tk.INSERT
        return self.area_texto.index(f"{inicio} linestart"), self.area_texto.index(f"{fim} lineend")

    def abrir_paragrafo(self):
        janela, corpo = self._criar_dialogo("Parágrafo")

        var_alinhamento = tk.StringVar(value="left")
        var_recuo_esq = tk.IntVar(value=0)
        var_recuo_primeira = tk.IntVar(value=0)
        var_recuo_dir = tk.IntVar(value=0)
        var_antes = tk.IntVar(value=0)
        var_depois = tk.IntVar(value=0)
        var_entrelinhas = tk.IntVar(value=0)
        var_escopo = tk.StringVar(value="selecao" if self.intervalo_selecao() else "tudo")

        # Lê a configuração atual do parágrafo onde está o cursor (se houver tag)
        for tag in self.area_texto.tag_names(tk.INSERT):
            if tag.startswith("par_"):
                cfg = {k: self.area_texto.tag_cget(tag, k) for k in
                       ("justify", "lmargin1", "lmargin2", "rmargin", "spacing1", "spacing3", "spacing2")}
                var_alinhamento.set(cfg["justify"] or "left")
                margem2 = int(float(cfg["lmargin2"] or 0))
                margem1 = int(float(cfg["lmargin1"] or 0))
                var_recuo_esq.set(margem2)
                var_recuo_primeira.set(margem1 - margem2)
                var_recuo_dir.set(int(float(cfg["rmargin"] or 0)))
                var_antes.set(int(float(cfg["spacing1"] or 0)))
                var_depois.set(int(float(cfg["spacing3"] or 0)))
                var_entrelinhas.set(int(float(cfg["spacing2"] or 0)))
                break

        alinh = ttk.LabelFrame(corpo, text="Alinhamento", padding=6)
        alinh.grid(row=0, column=0, columnspan=2, sticky="we")
        for texto, valor in (("Esquerda", "left"), ("Centralizado", "center"), ("Direita", "right")):
            ttk.Radiobutton(alinh, text=texto, value=valor,
                            variable=var_alinhamento).pack(side=tk.LEFT, padx=(0, 12))

        recuos = ttk.LabelFrame(corpo, text="Recuo (pixels)", padding=6)
        recuos.grid(row=1, column=0, sticky="nwe", pady=(10, 0))
        espacos = ttk.LabelFrame(corpo, text="Espaçamento (pixels)", padding=6)
        espacos.grid(row=1, column=1, sticky="nwe", pady=(10, 0), padx=(10, 0))

        def linha_campo(pai, rotulo, variavel, linha, maximo=400):
            ttk.Label(pai, text=rotulo).grid(row=linha, column=0, sticky="w", pady=2)
            ttk.Spinbox(pai, from_=0, to=maximo, textvariable=variavel, width=6).grid(
                row=linha, column=1, sticky="w", padx=(8, 0), pady=2)

        linha_campo(recuos, "Esquerda:", var_recuo_esq, 0)
        linha_campo(recuos, "Primeira linha:", var_recuo_primeira, 1)
        linha_campo(recuos, "Direita:", var_recuo_dir, 2)
        linha_campo(espacos, "Antes do parágrafo:", var_antes, 0, 200)
        linha_campo(espacos, "Depois do parágrafo:", var_depois, 1, 200)
        linha_campo(espacos, "Entre linhas:", var_entrelinhas, 2, 100)

        escopo = ttk.LabelFrame(corpo, text="Aplicar em", padding=6)
        escopo.grid(row=2, column=0, columnspan=2, sticky="we", pady=(10, 0))
        ttk.Radiobutton(escopo, text="Parágrafo(s) selecionado(s)", value="selecao",
                        variable=var_escopo).pack(side=tk.LEFT)
        ttk.Radiobutton(escopo, text="Documento inteiro", value="tudo",
                        variable=var_escopo).pack(side=tk.LEFT, padx=(14, 0))

        def valor(variavel):
            try:
                return max(0, int(variavel.get()))
            except (tk.TclError, ValueError):
                return 0

        def aplicar():
            config = dict(
                justify=var_alinhamento.get(),
                lmargin1=valor(var_recuo_esq) + valor(var_recuo_primeira),
                lmargin2=valor(var_recuo_esq),
                rmargin=valor(var_recuo_dir),
                spacing1=valor(var_antes),
                spacing2=valor(var_entrelinhas),
                spacing3=valor(var_depois),
            )
            self.aplicar_paragrafo(config, var_escopo.get())
            janela.destroy()

        botoes = ttk.Frame(corpo)
        botoes.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(botoes, text="Cancelar", command=janela.destroy).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="OK", command=aplicar).pack(side=tk.RIGHT, padx=(0, 6))
        janela.bind("<Return>", lambda e: aplicar())

    def aplicar_paragrafo(self, config, escopo="selecao"):
        if escopo == "tudo":
            inicio, fim = "1.0", "end-1c"
        else:
            inicio, fim = self.linhas_alvo()
        self.contador_paragrafo += 1
        nome_tag = f"par_{self.contador_paragrafo}"
        self.area_texto.tag_configure(nome_tag, **config)
        for tag in self.area_texto.tag_names():
            if tag.startswith("par_") and tag != nome_tag:
                self.area_texto.tag_remove(tag, inicio, fim)
        self.area_texto.tag_add(nome_tag, inicio, fim)

    # ════════════════════════════════════════════════════════════════
    # EDITAR ▸ INSERIR TABELA
    # ════════════════════════════════════════════════════════════════
    def abrir_inserir_tabela(self):
        janela, corpo = self._criar_dialogo("Inserir tabela")

        var_linhas = tk.IntVar(value=3)
        var_colunas = tk.IntVar(value=3)
        var_largura = tk.IntVar(value=12)
        var_cabecalho = tk.BooleanVar(value=True)
        var_estilo = tk.StringVar(value="grade")

        ttk.Label(corpo, text="Linhas:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Spinbox(corpo, from_=1, to=100, textvariable=var_linhas, width=6).grid(
            row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(corpo, text="Colunas:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(corpo, from_=1, to=30, textvariable=var_colunas, width=6).grid(
            row=1, column=1, sticky="w", padx=(8, 0))
        ttk.Label(corpo, text="Largura da célula (caracteres):").grid(
            row=2, column=0, sticky="w", pady=3)
        ttk.Spinbox(corpo, from_=3, to=60, textvariable=var_largura, width=6).grid(
            row=2, column=1, sticky="w", padx=(8, 0))

        ttk.Checkbutton(corpo, text="Primeira linha é cabeçalho",
                        variable=var_cabecalho).grid(row=3, column=0, columnspan=2,
                                                     sticky="w", pady=(6, 0))

        estilo = ttk.LabelFrame(corpo, text="Estilo das bordas", padding=6)
        estilo.grid(row=4, column=0, columnspan=2, sticky="we", pady=(8, 0))
        for texto, valor_estilo in (("Grade  ┌─┬─┐", "grade"), ("Simples +-+-+", "simples"),
                                    ("Markdown |---|", "markdown")):
            ttk.Radiobutton(estilo, text=texto, value=valor_estilo,
                            variable=var_estilo).pack(anchor="w")

        previa = tk.Text(corpo, height=7, width=44, font=self.fonte_mono,
                         relief="groove", state=tk.DISABLED, bg="#f7f7f7")
        previa.grid(row=0, column=2, rowspan=5, sticky="nsew", padx=(14, 0))

        def valor(variavel, minimo, padrao):
            try:
                return max(minimo, int(variavel.get()))
            except (tk.TclError, ValueError):
                return padrao

        def parametros(limite=False):
            linhas = valor(var_linhas, 1, 3)
            colunas = valor(var_colunas, 1, 3)
            largura = valor(var_largura, 3, 12)
            if limite:  # a prévia mostra no máximo 4x4 com células menores
                linhas, colunas, largura = min(linhas, 4), min(colunas, 4), min(largura, 8)
            return dict(linhas=linhas, colunas=colunas, largura=largura,
                        cabecalho=var_cabecalho.get(), estilo=var_estilo.get())

        def atualizar_previa(*_):
            previa.configure(state=tk.NORMAL)
            previa.delete("1.0", tk.END)
            previa.insert("1.0", self.gerar_tabela(**parametros(limite=True)))
            previa.configure(state=tk.DISABLED)

        for variavel in (var_linhas, var_colunas, var_largura, var_cabecalho, var_estilo):
            variavel.trace_add("write", atualizar_previa)
        atualizar_previa()

        def inserir():
            self.inserir_tabela(self.gerar_tabela(**parametros()))
            janela.destroy()

        botoes = ttk.Frame(corpo)
        botoes.grid(row=5, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(botoes, text="Cancelar", command=janela.destroy).pack(side=tk.RIGHT)
        ttk.Button(botoes, text="Inserir", command=inserir).pack(side=tk.RIGHT, padx=(0, 6))
        janela.bind("<Return>", lambda e: inserir())

    @staticmethod
    def gerar_tabela(linhas=3, colunas=3, largura=12, cabecalho=True, estilo="grade"):
        """Monta uma tabela em texto (caracteres de caixa, ASCII ou Markdown)."""
        celula_vazia = " " * largura
        celulas_cab = [f" {('Coluna ' + str(i + 1)).ljust(largura - 2)[:largura - 2]} "
                       for i in range(colunas)]

        if estilo == "markdown":
            saida = []
            primeira = celulas_cab if cabecalho else [celula_vazia] * colunas
            saida.append("|" + "|".join(primeira) + "|")
            saida.append("|" + "|".join("-" * largura for _ in range(colunas)) + "|")
            restantes = linhas - 1 if cabecalho else linhas
            for _ in range(max(0, restantes)):
                saida.append("|" + "|".join([celula_vazia] * colunas) + "|")
            return "\n".join(saida) + "\n"

        if estilo == "simples":
            topo = meio = base = "+" + "+".join("-" * largura for _ in range(colunas)) + "+"
            v = "|"
        else:  # grade
            topo = "┌" + "┬".join("─" * largura for _ in range(colunas)) + "┐"
            meio = "├" + "┼".join("─" * largura for _ in range(colunas)) + "┤"
            base = "└" + "┴".join("─" * largura for _ in range(colunas)) + "┘"
            v = "│"

        saida = [topo]
        for indice in range(linhas):
            if indice == 0 and cabecalho:
                saida.append(v + v.join(celulas_cab) + v)
            else:
                saida.append(v + v.join([celula_vazia] * colunas) + v)
            saida.append(meio if indice < linhas - 1 else base)
        return "\n".join(saida) + "\n"

    def inserir_tabela(self, texto_tabela):
        """Insere a tabela em uma linha própria, com fonte monoespaçada para alinhar as bordas."""
        self.area_texto.edit_separator()
        if self.area_texto.compare(tk.INSERT, "!=", f"{tk.INSERT} linestart"):
            self.area_texto.insert(tk.INSERT, "\n")
        inicio = self.area_texto.index(tk.INSERT)
        self.area_texto.insert(tk.INSERT, texto_tabela)
        fim = self.area_texto.index(tk.INSERT)
        # a tabela não deve herdar fonte/parágrafo do texto ao redor (desalinharia as bordas)
        for tag in self.area_texto.tag_names():
            if tag.startswith(("fonte_", "par_")):
                self.area_texto.tag_remove(tag, inicio, fim)
        self.area_texto.tag_add("tabela_mono", inicio, fim)
        self.area_texto.tag_raise("tabela_mono")
        self.area_texto.edit_separator()
        self.area_texto.see(tk.INSERT)
        self.area_texto.focus_set()


if __name__ == "__main__":
    app = EditorNotas()
    app.mainloop()