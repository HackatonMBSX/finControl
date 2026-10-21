"""Roteiro de ponta a ponta no navegador (Playwright). Ver e2e/README.md. Grava docs/e2e-resultado.json."""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/"
errs = []
total = 0


def check(cond, msg):
    global total
    total += 1
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: errs.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 420, "height": 900})
    pg = ctx.new_page()
    logs = []
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: logs.append("pageerror: " + str(e)))
    dialogos = []

    def _dialogo(d):
        dialogos.append(d.message)
        d.accept()
    pg.on("dialog", _dialogo)

    def mes(acao):
        """‹ e › só existem no desktop; no celular o mês muda pelo calendário. Vai a 1366px, clica e volta a 420px."""
        pg.set_viewport_size({"width": 1366, "height": 800})
        pg.click(f"[data-act={acao}]")
        pg.set_viewport_size({"width": 420, "height": 900})

    def anima():
        """Nome da animação CSS do primeiro card atrasado (só existe na aba Despesas)."""
        return pg.evaluate("getComputedStyle(document.querySelector('.task.crit')).animationName")

    def sem_pulso():
        return pg.evaluate("document.body.classList.contains('sem-pulso')")

    pg.goto(URL)
    pg.wait_for_selector("#authForm")
    check("Entrar" in pg.inner_text("#app"), "tela de login aparece sem sessão")
    check(not pg.is_visible("#tabbar"), "tabbar escondida no login")

    # desktop: campos digitáveis de verdade (clique + teclado; nada pode cobrir o formulário)
    pg.set_viewport_size({"width": 1366, "height": 800})
    for nome in ("email", "senha"):
        pg.click(f"input[name={nome}]", timeout=3000); pg.keyboard.type("abc")
        check(pg.input_value(f"input[name={nome}]") == "abc", f"desktop: digita no campo {nome}")
        pg.fill(f"input[name={nome}]", "")
    pg.set_viewport_size({"width": 420, "height": 900})

    # login errado
    pg.fill("input[name=email]", "naoexiste@x.com"); pg.fill("input[name=senha]", "qualquer")
    pg.click("button[type=submit]")
    pg.wait_for_selector("#authErro:not(:empty)")
    check("incorretos" in pg.inner_text("#authErro"), "login inválido mostra erro amigável")

    # cadastro
    pg.click("#authAlternar")
    pg.fill("input[name=familia]", "Família Teste"); pg.fill("input[name=nome]", "Alvaro")
    pg.fill("input[name=email]", "alvaro@teste.com"); pg.fill("input[name=senha]", "Senha-forte-123")
    pg.check("input[name=lgpd]")
    pg.click("button[type=submit]")
    pg.wait_for_selector("#tabbar button", timeout=15000)
    pg.wait_for_function("document.querySelector('#app').innerText.length > 50")
    check("Início" in pg.inner_text("#viewTitle"), "entrou no app após cadastro")

    # categorias padrão criadas para família nova
    pg.click("#tabbar button[data-tab=cadastros]")
    check("Alugueis" in pg.inner_text("#app"), "categorias padrão criadas na família nova")

    # família nova: nada de dados fictícios em nenhuma aba
    FICT = ["Rafael", "Mariana", "Sofia", "Carlos", "Bradesco", "Nubank", "BTG", "familia.com", "sk_sandbox", "Unistalda", "182 ms"]
    for tab in ("inicio", "despesas", "analises", "cadastros", "ajustes"):
        pg.click(f"#tabbar button[data-tab={tab}]"); pg.wait_for_timeout(300)
        t = pg.inner_text("#app")
        achou = [w for w in FICT if w.lower() in t.lower()]
        check(not achou, f"aba {tab} sem dados fictícios {achou}")
        pg.screenshot(path=f"/tmp/e2e_vazio_{tab}.png", full_page=True)
    check(pg.locator("[data-act=exemplo]").count() == 0, "não existe botão de carregar exemplo")
    pg.click("#tabbar button[data-tab=despesas]")
    check(pg.locator(".col .task").count() == 0, "nenhuma despesa em família nova")

    # Asaas: salvar, mascarar e testar sem inventar resposta
    pg.click("#tabbar button[data-tab=ajustes]")
    pg.fill("#asaasKey", "sk_teste_1234567890abcd"); pg.select_option("#asaasAmb", "producao")
    pg.click("[data-act=salvarAsaas]")
    pg.wait_for_function("document.querySelector('#asaasKey').placeholder.includes('abcd')")
    check("sk_teste_1234567890abcd" not in pg.content(), "chave do Asaas não volta inteira para a tela")
    pg.click("[data-act=testarAsaas]")
    pg.wait_for_selector("#sheetBody .alert")
    check("ainda não está ativa" in pg.inner_text("#sheetBody"), "teste do Asaas é honesto sobre a integração não estar ativa")
    pg.click("#sheetClose")

    # despesas criadas à mão (uma com vencimento passado = atrasada)
    pg.click("#tabbar button[data-tab=despesas]")
    for nome, valor, dia in (("Aluguel", "1500", "1"), ("Internet", "120", "28")):
        pg.click("[data-act=newdesp]")
        pg.fill("#sheetForm input[name=descricao]", nome); pg.fill("#sheetForm input[name=valor]", valor)
        pg.fill("#sheetForm input[name=dia]", dia)
        if nome == "Aluguel": pg.check("#sheetForm input[name=recorrente]")
        pg.click("#sheetForm button[type=submit]")
        pg.wait_for_function(f"document.body.innerText.includes('{nome}')")
    check(pg.locator(".col.c-atrasada .task", has_text="Aluguel").count() == 1, "despesa com vencimento passado cai em Atrasadas")
    pg.screenshot(path="/tmp/e2e_despesas.png")

    # criar despesa
    pg.click("[data-act=newdesp]")
    pg.fill("#sheetForm input[name=descricao]", "Teste E2E"); pg.fill("#sheetForm input[name=valor]", "123.45")
    pg.fill("#sheetForm input[name=dia]", "25")
    pg.click("#sheetForm button[type=submit]")
    pg.wait_for_function("document.body.innerText.includes('Teste E2E')")
    check(True, "despesa criada aparece no board")
    # pagar
    card = pg.locator(".task", has_text="Teste E2E").first
    card.locator("[data-act=pay]").click()
    pg.wait_for_function("document.querySelector('.col.c-pagas').innerText.includes('Teste E2E')")
    check(True, "pagar move para coluna Pagas")
    # excluir
    pg.locator(".task", has_text="Teste E2E").first.locator("[data-act=del]").click()
    pg.wait_for_function("!document.body.innerText.includes('Teste E2E')")
    check(True, "excluir remove do board")

    # alertas visuais pulsantes: ligados por padrão; o switch de Ajustes desliga e a escolha fica no aparelho
    check(anima() == "cardPulse", "pulsantes ligados por padrão: card atrasado anima")
    pg.click("#tabbar button[data-tab=ajustes]")
    check(pg.get_attribute("[data-act=togglePulso]", "aria-pressed") == "true", "switch de pulsantes começa ligado")
    pg.click("[data-act=togglePulso]")
    check(sem_pulso() and pg.get_attribute("[data-act=togglePulso]", "aria-pressed") == "false", "switch desliga os pulsantes")
    pg.click("#tabbar button[data-tab=despesas]")
    check(anima() == "none", "com pulsantes desligados o card atrasado não anima")
    pg.reload(); pg.wait_for_selector("#tabbar button")
    check(sem_pulso(), "escolha dos pulsantes persiste após recarregar")
    pg.click("#tabbar button[data-tab=ajustes]"); pg.click("[data-act=togglePulso]")
    pg.click("#tabbar button[data-tab=despesas]")
    check(not sem_pulso() and anima() == "cardPulse", "religar os pulsantes volta a animar")

    # header: ícone + título, sem subtítulo; no celular só sino + mês/ano, sem itens sobrepostos
    check(pg.locator("#viewSub").count() == 0, "header sem subtítulo")
    check(pg.is_visible("#soundToggle") and pg.is_visible("#mesBadge"), "celular: sino e mês/ano visíveis")
    check(not pg.is_visible("[data-act=mesAnt]") and not pg.is_visible("[data-act=mesProx]"), "celular: setas ‹ › escondidas")
    for largura in (420, 360, 320):
        pg.set_viewport_size({"width": largura, "height": 800})
        ok = pg.evaluate("""(() => {
            const a = document.querySelector('.brand').getBoundingClientRect();
            const b = document.querySelector('.top-actions').getBoundingClientRect();
            return a.right <= b.left + 1 && document.documentElement.scrollWidth <= window.innerWidth;
        })()""")
        check(ok, f"celular {largura}px: header sem sobreposição nem rolagem lateral")
    pg.set_viewport_size({"width": 1366, "height": 800})
    check(pg.is_visible("[data-act=mesAnt]") and pg.is_visible("[data-act=mesProx]"), "desktop: setas ‹ › continuam visíveis")
    pg.click("#mesBadge")
    check(not pg.evaluate("document.body.classList.contains('sheet-open')"), "desktop: clicar no mês não abre o calendário")
    pg.set_viewport_size({"width": 420, "height": 900})

    # calendário de competência (só no celular): ano, mês, fechar e restaurar
    rotulo0 = pg.inner_text("#mesBadge")
    pg.click("#mesBadge")
    pg.wait_for_function("document.body.classList.contains('sheet-open')")
    check(pg.locator(".cal-mes").count() == 12, "celular: tocar no mês abre o calendário com 12 meses")
    c0 = pg.get_attribute(".cal-mes.on", "data-c")
    ano0 = int(pg.inner_text(".cal-ano strong"))
    pg.click("[data-act=calAno][data-d='1']")
    check(int(pg.inner_text(".cal-ano strong")) == ano0 + 1, "calendário troca o ano")
    pg.click("[data-act=calAno][data-d='-1']")
    c1 = pg.locator(".cal-mes:not(.on)").first.get_attribute("data-c")
    pg.click(f".cal-mes[data-c='{c1}']")
    check(not pg.evaluate("document.body.classList.contains('sheet-open')") and pg.inner_text("#mesBadge") != rotulo0,
          "escolher um mês fecha o calendário e muda a competência")
    pg.click("#mesBadge"); pg.click(f".cal-mes[data-c='{c0}']")
    check(pg.inner_text("#mesBadge") == rotulo0, "calendário volta ao mês original")

    # rolagem: ações que gravam não levam a tela ao topo; trocar de aba leva
    pg.click("#tabbar button[data-tab=ajustes]")
    pg.evaluate("window.scrollTo(0, 300)")
    y0 = pg.evaluate("window.scrollY")
    classe0 = pg.get_attribute("[data-act=toggleSom]", "class")
    pg.click("[data-act=toggleSom]")
    pg.wait_for_function("c => document.querySelector('[data-act=toggleSom]').className !== c", arg=classe0)
    check(y0 > 0 and abs(pg.evaluate("window.scrollY") - y0) <= 2, "alternar alertas sonoros não leva a tela ao topo")
    pg.click("[data-act=toggleSom]")
    pg.wait_for_function("c => document.querySelector('[data-act=toggleSom]').className === c", arg=classe0)
    pg.click("#tabbar button[data-tab=inicio]")
    check(pg.evaluate("window.scrollY") == 0, "trocar de aba volta ao topo")

    # navegar meses + gerar mês
    pg.click("#tabbar button[data-tab=despesas]")
    mes("mesProx")
    check("Novembro" in pg.inner_text("#mesBadge") or "Dezembro" in pg.inner_text("#mesBadge") or "Outubro" not in pg.inner_text("#mesBadge"), "badge muda de mês")
    pg.click("[data-act=gerarMes]")
    pg.wait_for_function("document.querySelectorAll('.col .task').length > 0", timeout=30000)
    check(pg.locator(".col .task").count() > 0, "gerar mês cria as recorrentes no mês seguinte")
    mes("mesAnt")

    # análises / início renderizam
    for tab in ("inicio", "analises", "cadastros", "ajustes"):
        pg.click(f"#tabbar button[data-tab={tab}]")
        check(len(pg.inner_text("#app")) > 100, f"aba {tab} renderiza")

    # backup: exportar → apagar → restaurar pelo arquivo → dados voltam
    pg.click("#tabbar button[data-tab=ajustes]")
    with pg.expect_download() as dl:
        pg.click("[data-act=exportar]")
    arq = os.path.join(tempfile.gettempdir(), "fincontrol-backup-e2e.json")
    dl.value.save_as(arq)
    conteudo = json.load(open(arq))
    check(conteudo["versao"] == 1 and len(conteudo["checksum"]) == 64, "exportar baixa backup com versão e checksum")
    n_desp = len(conteudo["dados"]["despesas"])
    pg.click("#tabbar button[data-tab=despesas]")
    mes("mesProx")
    pg.locator(".task [data-act=del]").first.click()
    pg.wait_for_timeout(800)
    mes("mesAnt")
    pg.click("#tabbar button[data-tab=ajustes]")
    m1 = []
    pg.on("dialog", lambda d: m1.append(d.message))
    pg.set_input_files("#arquivoBackup", arq)
    pg.wait_for_timeout(2500)
    pg.click("[data-act=historicoBackups]")
    pg.wait_for_selector("[data-act=baixarBackup]")
    check(pg.locator("[data-act=restaurarHistorico]").count() >= 2, "histórico lista exportação e backup automático")
    pg.click("#sheetClose")
    doc = pg.evaluate("fetch('/api/v1/despesas',{headers:{Authorization:'Bearer '+sessionStorage.getItem('fincontrol.token')}}).then(r=>r.json())")
    check(len(doc) == n_desp, f"restaurar devolve as {n_desp} despesas do backup")
    # arquivo adulterado é recusado
    conteudo["dados"]["despesas"][0]["valor"] = 1
    json.dump(conteudo, open(arq, "w"))
    msgs = []
    pg.on("dialog", lambda d: msgs.append(d.message))
    pg.set_input_files("#arquivoBackup", arq)
    pg.wait_for_timeout(2000)
    check(any("checksum" in m or "corrompido" in m for m in msgs), "arquivo adulterado é recusado com mensagem clara")

    # recarregar mantém sessão
    pg.reload(); pg.wait_for_selector("#tabbar button")
    check("Início" in pg.inner_text("#viewTitle"), "sessão persiste após recarregar")
    pg.click("#tabbar button[data-tab=despesas]")
    check(pg.locator(".col .task").count() > 0, "dados persistem após recarregar (vêm da API)")

    # sair e voltar
    pg.click("#tabbar button[data-tab=ajustes]")
    pg.click("[data-act=sair]")
    pg.wait_for_selector("#authForm")
    pg.fill("input[name=email]", "alvaro@teste.com"); pg.fill("input[name=senha]", "Senha-forte-123")
    pg.click("button[type=submit]"); pg.wait_for_selector("#tabbar button")
    check(True, "logout e novo login funcionam")

    # leitor: somente leitura
    pg.click("#tabbar button[data-tab=cadastros]"); pg.click("[data-act=cad][data-c=usuarios]")
    pg.fill("#novoUserNome", "Leitora"); pg.fill("#novoUserEmail", "leitora@teste.com"); pg.fill("#novoUserSenha", "Senha-forte-123")
    pg.select_option("#novoUserPapel", "leitor"); pg.click("[data-act=addUser]")
    pg.wait_for_function("document.body.innerText.includes('leitora@teste.com')")
    check(True, "admin cria usuário leitor")
    pg.evaluate("sessionStorage.clear()"); pg.reload(); pg.wait_for_selector("#authForm")
    pg.fill("input[name=email]", "leitora@teste.com"); pg.fill("input[name=senha]", "Senha-forte-123")
    pg.click("button[type=submit]"); pg.wait_for_selector("#tabbar button")
    pg.click("#tabbar button[data-tab=despesas]")
    check(not pg.locator("[data-act=newdesp]").is_visible(), "leitor não vê botão de nova despesa")
    check(not pg.locator(".task-actions").first.is_visible(), "leitor não vê ações nos cards")
    check(pg.locator(".col .task").count() > 0, "leitor enxerga as despesas")

    pg.screenshot(path=os.path.join(tempfile.gettempdir(), "e2e_leitor.png"))

    # excluir a própria conta (leitora): senha errada recusa, senha certa exclui e não entra mais
    def entra(email, senha="Senha-forte-123"):
        pg.fill("input[name=email]", email); pg.fill("input[name=senha]", senha)
        pg.click("button[type=submit]"); pg.wait_for_timeout(1200)
        return pg.locator("#tabbar button").count() > 0

    pg.click("#tabbar button[data-tab=ajustes]")
    check(not pg.locator("[data-act=excluirFamilia]").is_visible(), "leitor não vê o botão de excluir família")
    pg.click("[data-act=excluirConta]")
    pg.fill("#sheetForm input[name=senha]", "senha-errada-123"); pg.click("#sheetForm button[type=submit]")
    pg.wait_for_function("document.body.classList.contains('sheet-open')")
    pg.wait_for_timeout(800)
    check(any("Senha incorreta" in m for m in dialogos), "excluir conta com senha errada é recusado")
    pg.fill("#sheetForm input[name=senha]", "Senha-forte-123"); pg.click("#sheetForm button[type=submit]")
    pg.wait_for_selector("#authForm")
    check(any("Conta excluída" in m for m in dialogos), "leitora exclui a própria conta e volta ao login")
    check(not entra("leitora@teste.com"), "conta excluída não consegue mais entrar")

    # último admin: barrado com a orientação; depois exclui a família e tudo some
    pg.reload(); pg.wait_for_selector("#authForm")
    check(entra("alvaro@teste.com"), "admin entra")
    pg.click("#tabbar button[data-tab=ajustes]")
    pg.click("[data-act=excluirConta]")
    pg.wait_for_timeout(500)
    check(any("único administrador" in m and "Exclua a família" in m for m in dialogos),
          "último admin é barrado com a orientação de excluir a família")
    check(pg.locator("#tabbar button").count() > 0, "admin continua logado depois de ser barrado")
    pg.click("[data-act=excluirFamilia]")
    pg.fill("#sheetForm input[name=senha]", "Senha-forte-123"); pg.click("#sheetForm button[type=submit]")
    pg.wait_for_selector("#authForm")
    check(any("Família excluída" in m for m in dialogos), "admin exclui a família e volta ao login")
    check(not entra("alvaro@teste.com"), "depois de excluir a família ninguém entra mais")
    b.close()

print("\nconsole:", *logs[:10], sep="\n  ")
print("\nFALHAS:", errs if errs else "nenhuma")
resultado = {"executadoEm": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"), "verificacoes": total,
             "falhas": len(errs)}
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "e2e-resultado.json")
json.dump(resultado, open(destino, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if errs else 0)
