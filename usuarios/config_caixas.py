from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent / "Bases"

RESPONSAVEIS_POR_CAIXA = {
    "MGI-SGP-DECIPEX-CGPAG-ANIST": [
        "daniela.almeida@gestao.gov.br",
        "joelma.nunes@gestao.gov.br",
        "juan.gois@gestao.gov.br",
        "valdereide.monteiro@gestao.gov.br",
    ],
    "MGI-SGP-DECIPEX-CGPAG-BENESP": [
        "claudia.r.silveira@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-CIVAC": [
        "Abilio.barbosa@gestao.gov.br",
        "lilian.eirado@gestao.gov.br",
        "luiz-claudio.silva@gestao.gov.br",
        "vivian.tomizawa@gestao.gov.br",
        "luiz.c.silva@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-CIVPAS": [
        "joao-batista.santos@gestao.gov.br",
        "waldemir.montes@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-CIVRES": [
        "Silvio.marques@gestao.gov.br",
        "adelaise.rodrigues@gestao.gov.br",
        "aldiani.saldanha@gestao.gov.br",
        "anderson.ferreira@gestao.gov.br",
        "andre.maggiotto@gestao.gov.br",
        "elson.aguiar@gestao.gov.br",
        "joabia.veloso@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-DEVIR": [
        "denise.b.costa@gestao.gov.br",
        "julio.netto@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-ESTPEN": [
        "aristides.lima@gestao.gov.br",
        "odete.pinto@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-EXANTE": [
        "jorge.feitoza@gestao.gov.br",
        "maiara.silva@gestao.gov.br",
        "marcelo.junior@gestao.gov.br",
        "marco.herminio@gestao.gov.br",
        "joao.ananias@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-JUD": [
        "cintia.nogueira@gestao.gov.br",
        "mauricio.ortiz@gestao.gov.br",
        "reinaldo.matos@gestao.gov.br",
        "sheila.conceicao@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-MILREP": [
        "ricardo.rocha@gestao.gov.br",
        "paulo.maciel@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-REVER": [
        "bruno.feitosa@gestao.gov.br",
        "joao.salvador@gestao.gov.br",
        "luciana.feitosa@gestao.gov.br",
        "maridete.figueira@gestao.gov.br",
        "victor-g.silva@gestao.gov.br"
    ],
    "MGI-SGP-DECIPEX-CGPAG-REPER": [
        "camilla.lopes@gestao.gov.br",
        "janine.maria@gestao.gov.br",
        "maria.h.conceicao@gestao.gov.br",
        "paulo.jara@gestao.gov.br",
        "tatiane.santana@gestao.gov.br"
    ],
}

METAS_POR_CAIXA = {
    "MGI-SGP-DECIPEX-CGPAG-ANIST": 4,
    "MGI-SGP-DECIPEX-CGPAG-BENESP": 7,
    "MGI-SGP-DECIPEX-CGPAG-CIVAC": 7,
    "MGI-SGP-DECIPEX-CGPAG-CIVPAS": 7,
    "MGI-SGP-DECIPEX-CGPAG-CIVRES": 4,
    "MGI-SGP-DECIPEX-CGPAG-DEVIR": 7,
    "MGI-SGP-DECIPEX-CGPAG-ESTPEN": 7,
    "MGI-SGP-DECIPEX-CGPAG-EXANTE": 6,
    "MGI-SGP-DECIPEX-CGPAG-JUD": 4,
    "MGI-SGP-DECIPEX-CGPAG-MILREP": 4,
    "MGI-SGP-DECIPEX-CGPAG-REVER": 6,
    "MGI-SGP-DECIPEX-CGPAG-REPER": 4,
}

CAIXAS = list(RESPONSAVEIS_POR_CAIXA.keys())

SE_PATH = Path(__file__).parent / "Bases"



