TOKEN="tokenofadminuser"
CLONE_ACCESS_TOKEN="token_to_clone_via_https"
SERVER="gitlab.your-domain.tld"
GITLAB_DIR="/opt/gitlab/"
REPOSITORY_DIR="/var/opt/gitlab/git-data/repositories"
BACKUP_DIR="/path/to/your/backups"
UPLOAD_DIR="/var/opt/gitlab/gitlab-rails/uploads"
TMP_DIR="/var/opt/gitlab/git-data/tmp""
ERROR_LOG="/var/log/gitlab/gitlab_backup_error.log"
LOG_TIMESTAMP="%d.%m.%Y %H:%M:%S"
LOG_ERRORS=True
TAR_TIMEOUT=500
GIT_TIMEOUT=500
API_TIMEOUT=15
LDAP_DN="cn=$USERNAME$,ou=users,ou=id,ou=auth,o=domain,c=tld"
