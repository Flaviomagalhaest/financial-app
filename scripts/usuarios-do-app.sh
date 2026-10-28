#!/usr/bin/env bash
# Usuários do app no user pool do Cognito, feitos pelo dono com a credencial dele (sem cadastro
# público: só os dois do casal existem, ADR 0002).
#
#   scripts/usuarios-do-app.sh listar <prod|dev>
#   scripts/usuarios-do-app.sh criar <prod|dev> <email>        # pede a senha, já definitiva
#   scripts/usuarios-do-app.sh desconectar <prod|dev> <email>  # celular perdido
#
# Desconectar revoga todos os refresh tokens do usuário (AdminUserGlobalSignOut): todo aparelho
# dele pede o login de novo. O token de acesso já emitido vale até vencer, no máximo 15 minutos.
set -euo pipefail

uso() { sed -n '5,7s/^#   //p' "$0" >&2; exit 2; }
[ $# -ge 2 ] || uso
ACAO=$1
AMBIENTE=$2
case "$AMBIENTE" in prod | dev) ;; *) uso ;; esac

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
REGIAO=$(jq -r .regiao "$RAIZ/config/aws.json")
POOL=$(aws cloudformation describe-stacks --region "$REGIAO" --stack-name "financial-$AMBIENTE-dados" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text)
cognito() { aws cognito-idp --region "$REGIAO" "$@" --user-pool-id "$POOL"; }

case "$ACAO" in
  listar)
    cognito list-users --query 'Users[].[Attributes[?Name==`email`]|[0].Value, UserStatus, Enabled]' --output table
    ;;
  criar)
    EMAIL=${3:?informe o e-mail}
    read -rsp "Senha de $EMAIL: " SENHA && echo
    read -rsp "Repita a senha: " DE_NOVO && echo
    [ "$SENHA" = "$DE_NOVO" ] || { echo "as senhas não batem" >&2; exit 1; }
    # Sem e-mail de convite e sem senha provisória: a senha já sai definitiva.
    cognito admin-create-user --username "$EMAIL" --message-action SUPPRESS \
      --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true >/dev/null
    cognito admin-set-user-password --username "$EMAIL" --password "$SENHA" --permanent
    echo "$EMAIL criado em $AMBIENTE"
    ;;
  desconectar)
    EMAIL=${3:?informe o e-mail}
    cognito admin-user-global-sign-out --username "$EMAIL"
    echo "sessões de $EMAIL em $AMBIENTE encerradas; o acesso já emitido vence em até 15 minutos"
    ;;
  *) uso ;;
esac
