# Bella Estética — Sistema de Gestão

Sistema web para clínica de estética com cadastro de clientes,
agendamentos e programa de fidelidade automático.

## Instalação

```bash
# 1. Instale as dependências
pip install -r requirements.txt

# 2. Rode o servidor
python app.py
```

Depois abra no celular ou computador: **http://localhost:5000**

Se quiser acessar pelo celular na mesma rede Wi-Fi, use o IP da máquina:
**http://SEU_IP:5000** (ex: http://192.168.1.10:5000)

## Funcionalidades

- **Dashboard** — visão geral de clientes, agendamentos e receita
- **Clientes** — cadastro completo com busca por nome, telefone ou e-mail
- **Agendamentos** — criação com desconto automático, concluir ou cancelar
- **Histórico** — perfil de cada cliente com todos os atendimentos
- **Fidelidade automática** — desconto aplicado ao fechar cada atendimento

## Programa de Fidelidade

| Visitas concluídas | Desconto |
|--------------------|----------|
| 0 – 4              | 0%       |
| 5 – 9              | 5%       |
| 10 – 19            | 10%      |
| 20+                | 15%      |

O desconto é recalculado automaticamente toda vez que um atendimento
é marcado como **concluído**.

## Estrutura

```
clinica/
├── app.py           # Servidor Flask + rotas
├── database.py      # Banco SQLite + lógica de fidelidade
├── requirements.txt
├── templates/       # Páginas HTML
│   ├── base.html
│   ├── index.html
│   ├── clientes.html
│   ├── form_cliente.html
│   ├── perfil_cliente.html
│   ├── agendamentos.html
│   └── form_agendamento.html
└── static/
    ├── css/style.css
    └── js/main.js
```

O banco de dados `clinica.db` é criado automaticamente na primeira execução.
