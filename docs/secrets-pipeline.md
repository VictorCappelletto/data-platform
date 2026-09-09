# Secrets pipeline (Docker + SOPS)

Criptografa **variável por variável**. Se `B` e `C` já estão encriptadas e `A` é nova, você adiciona só `A` — as outras não são reescritas.

## Conceito

```text
encrypted-secrets/local.env     ← commitado (valores ENC[...])
encrypted-secrets/.age-key      ← NUNCA commitar (chave privada)
encrypted-secrets/.age.pub      ← commitado (chave pública)
.env                            ← gerado localmente (decrypt)
```

Ferramentas dentro do container Docker: **SOPS** + **age**.

## Primeira vez

```powershell
make secrets-init
```

Isso gera as chaves age e um arquivo `encrypted-secrets/local.env` vazio (já criptografado).

## Adicionar só variáveis novas (seu caso A, B, C)

**Cenário:** `VAR_B` e `VAR_C` já encriptadas; `VAR_A` ainda não.

1. Crie um arquivo só com a nova variável:

```powershell
echo "VAR_A=valor-secreto-a" > config/env/secrets.pending.env
```

2. Adicione ao store (só `A` é tocada):

```powershell
make secrets-add FILE=config/env/secrets.pending.env
```

3. Gere o `.env` para Docker / apps:

```powershell
make secrets-decrypt
make up
```

## Outros comandos

| Comando | O que faz |
|---------|-----------|
| `make secrets-set KEY=VALUE` | Encripta/atualiza uma variável |
| `make secrets-status` | Lista chaves: `encrypted` vs `plaintext` |
| `make secrets-edit` | Editor interativo (SOPS) |
| `make secrets-export` | Imprime `.env` no stdout |

Exemplos:

```powershell
make secrets-set MSSQL_SA_PASSWORD=Olist@Dev123!
make secrets-set AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..."
make secrets-status
```

## Uso com Docker Compose

`make up` e `make sql-up` rodam **`env-prepare` automaticamente** antes de subir containers:

1. Bootstrap de secrets faltantes (`config/env/secrets.bootstrap.env`)
2. Merge `.env.example` + secrets decriptados → `.env`

```powershell
make env-prepare          # manual
make azure-verify-rg      # valida RG no Azure vs .env
make up                   # env-prepare + compose
```

## CI / GitHub Actions

1. Commitar `encrypted-secrets/local.env` (ciphertext)
2. Guardar a chave privada age em **GitHub Secret** `SOPS_AGE_KEY` (conteúdo de `.age-key`)
3. No workflow, antes do deploy:

```yaml
- name: Decrypt secrets
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    echo "$SOPS_AGE_KEY" > encrypted-secrets/.age-key
    make secrets-decrypt
```

## Chaves encriptadas

Todas as variáveis em `encrypted-secrets/local.env` são encriptadas (arquivo dedicado só a secrets).

## Segurança

| Arquivo | Commitar? |
|---------|-----------|
| `encrypted-secrets/local.env` | Sim (ciphertext) |
| `encrypted-secrets/.age.pub` | Sim |
| `encrypted-secrets/.age-key` | **Nunca** |
| `.env` | **Nunca** |
| `config/env/secrets.pending.env` | **Nunca** (temporário) |
