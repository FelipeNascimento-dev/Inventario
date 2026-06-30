// MENU DROPDOWN

//localStorage.clear();

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.dropdown').forEach((dropdown) => {
    const dropbtn = dropdown.querySelector('.dropbtn');
    const dropdownContent = dropdown.querySelector('.dropdown-content');
    if (!dropbtn || !dropdownContent) {
      return;
    }

    function closeDropdown() {
      dropdown.classList.remove('open');
      dropbtn.classList.remove('hover-active');
      if (dropbtn.tagName === 'BUTTON') {
        dropbtn.setAttribute('aria-expanded', 'false');
      }
    }

    dropbtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = dropdown.classList.contains('open');
      document.querySelectorAll('.dropdown.open').forEach((other) => {
        if (other !== dropdown) {
          other.classList.remove('open');
          const otherBtn = other.querySelector('.dropbtn');
          if (otherBtn) {
            otherBtn.classList.remove('hover-active');
            if (otherBtn.tagName === 'BUTTON') {
              otherBtn.setAttribute('aria-expanded', 'false');
            }
          }
        }
      });
      closeDropdown();
      if (!isOpen) {
        dropdown.classList.add('open');
        dropbtn.classList.add('hover-active');
        if (dropbtn.tagName === 'BUTTON') {
          dropbtn.setAttribute('aria-expanded', 'true');
        }
      }
    });

    document.addEventListener('click', function (e) {
      if (!dropdown.contains(e.target)) {
        closeDropdown();
      }
    });
  });
});

// submenu dropdown

document.querySelectorAll('.column-toggle').forEach(toggle => {
  toggle.addEventListener('click', () => {
    const targetId = toggle.getAttribute('data-target');
    const targetMenu = document.getElementById(targetId);

    document.querySelectorAll('.submenu').forEach(menu => {
      if (menu.id !== targetId) {
        menu.style.display = 'none';
      }
    });

    targetMenu.style.display = (targetMenu.style.display === 'flex') ? 'none' : 'flex';
  });
});

document.querySelectorAll('.submenu-toggle').forEach(subToggle => {
  subToggle.addEventListener('click', () => {
    const subId = subToggle.getAttribute('data-target');
    const subMenu = document.getElementById(subId);

    subMenu.style.display = (subMenu.style.display === 'block') ? 'none' : 'block';
  });
});

function toggleUsuarioMenu() {
  const menu = document.getElementById("usuario-menu");
  menu.style.display = menu.style.display === "block" ? "none" : "block";
  // fecha se clicar fora
  document.addEventListener('click', function handler(e) {
    if (!menu.contains(e.target) && !e.target.classList.contains("usuario-logado")) {
      menu.style.display = "none";
      document.removeEventListener('click', handler);
    }
  });
}

// DATA E HORA ROMANEIOS

document.addEventListener('DOMContentLoaded', function () {
  const dataInput = document.getElementById('data');
  const horaInput = document.getElementById('hora');

  if (dataInput && horaInput) {
    function atualizarDataHora() {
      const agora = new Date();

      const dataFormatada = agora.toLocaleDateString('pt-BR');

      const horaFormatada = agora.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });

      dataInput.value = dataFormatada;
      horaInput.value = horaFormatada;
    }

    atualizarDataHora();
    setInterval(atualizarDataHora, 1000);
  }
});

// CONTADOR ROMANEIOS

document.addEventListener('DOMContentLoaded', function () {
  // Função para gerar o código de rastreio
  function gerarCodigoRastreio(siglaEstado) {
    const agora = new Date();
    const dia = String(agora.getDate()).padStart(2, '0');
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    const ano = String(agora.getFullYear()).slice(-2);
    const hora = String(agora.getHours()).padStart(2, '0');
    const minuto = String(agora.getMinutes()).padStart(2, '0');

    return `${siglaEstado.toUpperCase()}${dia}${mes}${ano}${hora}${minuto}BR`;
  }

  // Função para obter a sigla do estado via IP
  async function obterEstadoDoUsuario() {
    try {
      const response = await fetch('https://ipapi.co/json/');
      const data = await response.json();
      return data.region_code || 'XX';
    } catch (error) {
      console.error('Erro ao obter localização do usuário:', error);
      return 'XX';
    }
  }

  const formulario = document.getElementById('form-romaneio');
  const btnRegistrar = document.getElementById('btn-registrar');
  const contadorDisplay = document.getElementById('contador');
  const tituloRomaneio = document.getElementById('titulo-romaneio');
  const modal = document.getElementById('modal-romaneio');
  const btnRevisar = document.getElementById('btn-revisar');
  const btnFecharModal = document.getElementById('btn-fechar-modal');
  const btnEncerrar = document.getElementById('btn-encerrar');
  const btnNaoEditar = document.getElementById('btn-nao-editar');

  if (formulario && contadorDisplay && tituloRomaneio) {
    let contadorRegistros = 0;
    let contadorRomaneio;
    const modoEdicao = localStorage.getItem('modoEdicao') === 'true';
    const romaneios = JSON.parse(localStorage.getItem('romaneios') || '{}');

    if (modoEdicao) {
      contadorRomaneio = Number(localStorage.getItem('romaneioEmEdicao')) || 1;
    } else {
      const numerosExistentes = Object.keys(romaneios).map(r => Number(r));
      const proximoNumero = numerosExistentes.length ? Math.max(...numerosExistentes) + 1 : 1;
      contadorRomaneio = proximoNumero;
      localStorage.setItem('romaneioEmEdicao', contadorRomaneio.toString().padStart(10, '0'));
    }

    function atualizarTituloRomaneio() {
      const numeroFormatado = contadorRomaneio.toString().padStart(10, '0');
      tituloRomaneio.textContent = `Romaneio ${numeroFormatado}`;
    }

    function atualizarContador() {
      const formatado = contadorRegistros.toString().padStart(2, '0');
      contadorDisplay.textContent = `${formatado}/30`;
    }

    function validarCampos() {
      const campos = formulario.querySelectorAll('input[required]');
      for (let campo of campos) {
        if (campo.offsetParent === null || campo.disabled) continue;
        if (!campo.value.trim()) {
          alert('Preencha todos os campos obrigatórios.');
          campo.focus();
          return false;
        }
      }
      return true;
    }

    function coletarDadosFormulario() {
      return {
        romaneio: contadorRomaneio.toString().padStart(10, '0'),
        serial: document.getElementById('serial')?.value || '',
        chamado: document.getElementById('chamado')?.value || '',
        data: document.getElementById('data')?.value || '',
        hora: document.getElementById('hora')?.value || '',
        usuario: document.getElementById('usuario')?.value || '',
        filial: document.getElementById('filial')?.value || '',
        destino: document.getElementById('destino')?.value || ''
      };
    }

    btnRegistrar?.addEventListener('click', function (e) {
      e.preventDefault();

      if (!validarCampos()) return;

      const dados = coletarDadosFormulario();
      const numeroRomaneioAtual = contadorRomaneio.toString().padStart(10, '0');
      const romaneiosObj = JSON.parse(localStorage.getItem('romaneios') || '{}');

      if (!romaneiosObj[numeroRomaneioAtual]) {
        romaneiosObj[numeroRomaneioAtual] = [];
      }

      romaneiosObj[numeroRomaneioAtual].push(dados);
      localStorage.setItem('romaneios', JSON.stringify(romaneiosObj));

      contadorRegistros++;
      atualizarContador();

      if (contadorRegistros >= 31 && modal) {
        modal.style.display = 'flex';
      }

      formulario.reset();
    });

    btnEncerrar?.addEventListener('click', async function () {
      if (contadorRegistros === 0) {
        alert('Você ainda não registrou nenhum item neste romaneio.');
        return;
      }

      if (modal) modal.style.display = 'flex';

      if (contadorRegistros >= 31) {
        alert('Este romaneio já atingiu o limite de 30 registros.');
        return;
      }
    });

    btnFecharModal?.addEventListener('click', async function () {
      if (modal) modal.style.display = 'none';

      const siglaEstado = await obterEstadoDoUsuario();
      const codigoRastreio = gerarCodigoRastreio(siglaEstado);

      const numeroRomaneioAtual = contadorRomaneio.toString().padStart(10, '0');
      const metadados = JSON.parse(localStorage.getItem('metadadosRomaneios') || '{}');
      metadados[numeroRomaneioAtual] = {
        codigoRastreio,
        dataCriacao: new Date().toISOString()
      };
      localStorage.setItem('metadadosRomaneios', JSON.stringify(metadados));

      console.log(`Código de rastreio gerado: ${codigoRastreio}`);

      contadorRegistros = 0;

      contadorRomaneio++;

      localStorage.setItem('romaneioEmEdicao', contadorRomaneio.toString().padStart(10, '0'));

      atualizarContador();
      atualizarTituloRomaneio();
    });

    btnNaoEditar?.addEventListener('click', async function () {
      const siglaEstado = await obterEstadoDoUsuario();
      const codigoRastreio = gerarCodigoRastreio(siglaEstado);

      const numeroRomaneioAtual = contadorRomaneio.toString().padStart(10, '0');
      const metadados = JSON.parse(localStorage.getItem('metadadosRomaneios') || '{}');
      metadados[numeroRomaneioAtual] = {
        codigoRastreio,
        dataCriacao: new Date().toISOString()
      };
      localStorage.setItem('metadadosRomaneios', JSON.stringify(metadados));

      contadorRegistros = 0;
      contadorRomaneio++;

      localStorage.setItem('romaneioEmEdicao', contadorRomaneio.toString().padStart(10, '0'));

      atualizarContador();
      atualizarTituloRomaneio();

      console.log(`Romaneio ${numeroRomaneioAtual} fechado. Código de rastreio gerado: ${codigoRastreio}`);
    });

    btnRevisar?.addEventListener('click', function () {
      localStorage.setItem('modoEdicao', 'true');
      localStorage.setItem('romaneioEmEdicao', contadorRomaneio.toString().padStart(10, '0'));

      window.location.href = 'revisar.html';
    });

    atualizarContador();
    atualizarTituloRomaneio();
  }
});