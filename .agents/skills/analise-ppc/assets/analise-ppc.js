(() => {
  const busca = document.getElementById("filtro-busca");
  const modo = document.getElementById("filtro-modo");
  const estado = document.getElementById("filtro-estado");
  const criticidade = document.getElementById("filtro-criticidade");
  const revisao = document.getElementById("filtro-revisao");
  const contador = document.getElementById("contador-visivel");
  const anotacoes = Array.from(document.querySelectorAll(".annotation-card.finding"));
  const marcadores = Array.from(document.querySelectorAll(".annotation-marker"));
  const destaques = Array.from(document.querySelectorAll(".evidence-link"));
  const blocos = Array.from(document.querySelectorAll(".ppc-block"));
  const margem = document.querySelector(".review-margin");

  if (!busca || !modo || !estado || !criticidade || !revisao || !contador) {
    return;
  }

  const marcadorPorAnotacao = new Map(
    marcadores.map((marcador) => [marcador.dataset.annotationRef, marcador])
  );
  const destaquesPorAnotacao = new Map();
  for (const destaque of destaques) {
    const id = destaque.dataset.evidenceRef;
    if (!id) {
      continue;
    }
    const lista = destaquesPorAnotacao.get(id) || [];
    lista.push(destaque);
    destaquesPorAnotacao.set(id, lista);
  }

  function normalizar(texto) {
    return (texto || "").toLocaleLowerCase("pt-BR");
  }

  function limparAtivos() {
    document.querySelectorAll(".is-active").forEach((item) => item.classList.remove("is-active"));
  }

  function destacar(id) {
    limparAtivos();
    const anotacao = document.getElementById(id);
    const marcador = marcadorPorAnotacao.get(id);
    if (anotacao) {
      anotacao.classList.add("is-active");
    }
    if (marcador) {
      marcador.classList.add("is-active");
      const bloco = marcador.closest(".ppc-block");
      if (bloco) {
        bloco.classList.add("is-active");
      }
    }
    for (const destaque of destaquesPorAnotacao.get(id) || []) {
      destaque.classList.add("is-active");
      const bloco = destaque.closest(".ppc-block");
      if (bloco) {
        bloco.classList.add("is-active");
      }
    }
  }

  function rolarNaMargem(anotacao) {
    if (!margem || !anotacao) {
      return;
    }
    const cabecalho = margem.querySelector(".margin-heading");
    const margemRect = margem.getBoundingClientRect();
    const anotacaoRect = anotacao.getBoundingClientRect();
    const cabecalhoAltura = cabecalho ? cabecalho.getBoundingClientRect().height : 0;
    const destino = margem.scrollTop + anotacaoRect.top - margemRect.top - cabecalhoAltura - 12;
    margem.scrollTo({ top: Math.max(0, destino), behavior: "smooth" });
  }

  function rolarNaPagina(elemento) {
    if (!elemento) {
      return;
    }
    elemento.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function revelarAnotacaoSeFiltrada(id) {
    const anotacao = document.getElementById(id);
    if (!anotacao || !anotacao.hidden) {
      return;
    }
    modo.value = "todos";
    aplicarFiltros();
  }

  function aplicarFiltros() {
    const termo = normalizar(busca.value);
    const somenteAcionaveis = modo.value === "acionaveis";
    document.body.dataset.annotationMode = modo.value;
    let visiveis = 0;

    for (const anotacao of anotacoes) {
      const okModo = !somenteAcionaveis || anotacao.dataset.acionavel === "sim";
      const textoBusca = anotacao.dataset.texto || anotacao.textContent;
      const okBusca = !termo || normalizar(textoBusca).includes(termo);
      const okEstado = !estado.value || anotacao.dataset.estado === estado.value;
      const okCriticidade = !criticidade.value || anotacao.dataset.criticidade === criticidade.value;
      const okRevisao = !revisao.value || anotacao.dataset.revisao === revisao.value;
      const visivel = okModo && okBusca && okEstado && okCriticidade && okRevisao;
      anotacao.hidden = !visivel;

      const marcador = marcadorPorAnotacao.get(anotacao.id);
      if (marcador) {
        marcador.hidden = !visivel;
      }
      if (visivel) {
        visiveis += 1;
      }
    }

    for (const bloco of blocos) {
      const marcadoresVisiveis = bloco.querySelectorAll(".annotation-marker:not([hidden])").length;
      bloco.dataset.annotations = String(marcadoresVisiveis);
    }

    contador.textContent = String(visiveis);
  }

  [busca, modo, estado, criticidade, revisao].forEach((elemento) => {
    elemento.addEventListener("input", aplicarFiltros);
    elemento.addEventListener("change", aplicarFiltros);
  });

  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-annotation-ref], [data-evidence-ref], .backlink");
    if (!link) {
      return;
    }
    const id = link.dataset.annotationRef || link.dataset.evidenceRef || link.getAttribute("href")?.slice(1);
    if (!id) {
      return;
    }
    event.preventDefault();
    history.replaceState(null, "", `#${id}`);
    revelarAnotacaoSeFiltrada(id);
    destacar(id);
    if (link.dataset.annotationRef || link.dataset.evidenceRef) {
      const alvo = document.getElementById(id);
      rolarNaMargem(alvo);
    } else {
      rolarNaPagina(document.getElementById(id));
    }
  });

  document.addEventListener("focusin", (event) => {
    const destaque = event.target.closest(".evidence-link[data-evidence-ref]");
    if (destaque?.dataset.evidenceRef) {
      destacar(destaque.dataset.evidenceRef);
    }
  });

  window.addEventListener("hashchange", () => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (id) {
      destacar(id);
    }
  });

  aplicarFiltros();
  if (window.location.hash) {
    destacar(decodeURIComponent(window.location.hash.slice(1)));
  }
})();
